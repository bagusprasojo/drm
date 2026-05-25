import io
import json
import zipfile
from pathlib import Path

import fitz
from celery import shared_task
from django.conf import settings

from drm.crypto_utils import (
    aes_gcm_encrypt,
    build_manifest,
    derive_page_key,
    encrypt_key_for_storage,
    ensure_dir,
    generate_content_key,
    load_master_key_from_env,
    rsa_sign,
    sha256_b64,
)
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

        content_key = generate_content_key()
        encrypted_content_key_b64 = encrypt_key_for_storage(master_key, content_key)

        doc = fitz.open(source_file)
        total_pages = len(doc)
        manifest_pages = []
        manifest_files = []

        def write_entry(zf: zipfile.ZipFile, name: str, data: bytes) -> None:
            zf.writestr(name, data)
            manifest_files.append({"path": name, "sha256": sha256_b64(data), "size": len(data)})

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

                page_key = derive_page_key(content_key, idx)
                encrypted_img = aes_gcm_encrypt(page_key, image_bytes)
                encrypted_txt = aes_gcm_encrypt(page_key, text_bytes)

                img_path = f"pages/p{idx}.img"
                txt_path = f"text/p{idx}.txt"
                img_blob = encrypted_img.nonce + encrypted_img.ciphertext
                txt_blob = encrypted_txt.nonce + encrypted_txt.ciphertext

                write_entry(zf, img_path, img_blob)
                write_entry(zf, txt_path, txt_blob)

                manifest_pages.append(
                    {
                        "page": idx,
                        "image": img_path,
                        "text": txt_path,
                        "nonce_len": 12,
                        "image_sha256": sha256_b64(img_blob),
                        "text_sha256": sha256_b64(txt_blob),
                    }
                )

            thumbnail = doc[0].get_pixmap(dpi=96).tobytes("png") if total_pages else b""
            write_entry(zf, "thumb/cover.png", thumbnail)

            metadata = {
                "ebook_id": ebook.id,
                "title": ebook.title,
                "author": ebook.author,
                "total_pages": total_pages,
            }
            metadata_bin = json.dumps(metadata, separators=(",", ":")).encode("utf-8")
            write_entry(zf, "metadata/book.json", metadata_bin)

            manifest_payload = {
                "version": 2,
                "package_format_version": 2,
                "content_key_alg": "AES-256-GCM",
                "page_key_kdf": "SHA256(content_key|page_number)",
                "ebook_id": ebook.id,
                "total_pages": total_pages,
                "files": manifest_files,
                "pages": manifest_pages,
            }
            manifest_bin = build_manifest(manifest_payload)
            signature = rsa_sign(settings.DRM_RSA_PRIVATE_KEY_PEM, manifest_bin)

            zf.writestr("manifest.bin", manifest_bin)
            zf.writestr("manifest.sig", signature)

        ebook.package_path = str(out_file)
        ebook.total_pages = total_pages
        ebook.status = Ebook.ProcessingStatus.READY
        ebook.package_format_version = 2
        ebook.encrypted_content_key_b64 = encrypted_content_key_b64
        ebook.save(update_fields=["package_path", "total_pages", "status", "package_format_version", "encrypted_content_key_b64"])
    except Exception:
        ebook.status = Ebook.ProcessingStatus.FAILED
        ebook.save(update_fields=["status"])
        raise
