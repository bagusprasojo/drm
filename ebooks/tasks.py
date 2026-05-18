import io
import json
import zipfile
from pathlib import Path

import fitz
from celery import shared_task
from django.conf import settings

from drm.crypto_utils import aes_gcm_encrypt, build_manifest, derive_page_key, ensure_dir, load_master_key_from_env, rsa_sign
from .models import Ebook


def _json_safe(value):
    if isinstance(value, bytes):
        return None
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_safe(v) for v in value]
    return value


@shared_task(bind=True, max_retries=1)
def process_ebook_task(self, ebook_id: int) -> None:
    ebook = Ebook.objects.get(id=ebook_id)
    ebook.status = Ebook.ProcessingStatus.PROCESSING
    ebook.save(update_fields=["status"])

    try:
        source_file = Path(ebook.source_path)
        if source_file.suffix.lower() != ".pdf":
            raise ValueError("Only PDF is supported")

        master_key = load_master_key_from_env(settings.DRM_MASTER_KEY_B64)
        ensure_dir(settings.PACKAGE_STORAGE_ROOT)

        doc = fitz.open(source_file)
        total_pages = len(doc)
        manifest_pages = []

        out_file = settings.PACKAGE_STORAGE_ROOT / f"ebook_{ebook.id}.bookpkg"
        with zipfile.ZipFile(out_file, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for idx, page in enumerate(doc, start=1):
                pix = page.get_pixmap(dpi=144)
                image_bytes = pix.tobytes("png")

                text_mapping = {
                    "page": idx,
                    "width": page.rect.width,
                    "height": page.rect.height,
                    "blocks": _json_safe(page.get_text("dict").get("blocks", [])),
                }
                text_bytes = json.dumps(text_mapping, separators=(",", ":")).encode("utf-8")

                page_key = derive_page_key(master_key, idx)
                encrypted_img = aes_gcm_encrypt(page_key, image_bytes)
                encrypted_txt = aes_gcm_encrypt(page_key, text_bytes)

                img_path = f"pages/p{idx}.img"
                txt_path = f"text/p{idx}.txt"

                zf.writestr(img_path, encrypted_img.nonce + encrypted_img.ciphertext)
                zf.writestr(txt_path, encrypted_txt.nonce + encrypted_txt.ciphertext)

                manifest_pages.append(
                    {
                        "page": idx,
                        "image": img_path,
                        "text": txt_path,
                        "nonce_len": 12,
                    }
                )

            thumbnail = doc[0].get_pixmap(dpi=96).tobytes("png") if total_pages else b""
            zf.writestr("thumb/cover.png", thumbnail)

            metadata = {
                "ebook_id": ebook.id,
                "title": ebook.title,
                "author": ebook.author,
                "total_pages": total_pages,
            }
            zf.writestr("metadata/book.json", json.dumps(metadata, separators=(",", ":")))

            manifest_payload = {
                "version": 1,
                "ebook_id": ebook.id,
                "total_pages": total_pages,
                "pages": manifest_pages,
            }
            manifest_bin = build_manifest(manifest_payload)
            signature = rsa_sign(settings.DRM_RSA_PRIVATE_KEY_PEM, manifest_bin)

            zf.writestr("manifest.bin", manifest_bin)
            zf.writestr("license.sig", signature)

        ebook.package_path = str(out_file)
        ebook.total_pages = total_pages
        ebook.status = Ebook.ProcessingStatus.READY
        ebook.save(update_fields=["package_path", "total_pages", "status"])
    except Exception:
        ebook.status = Ebook.ProcessingStatus.FAILED
        ebook.save(update_fields=["status"])
        raise
