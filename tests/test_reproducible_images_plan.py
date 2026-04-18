from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ReproducibleImageSourceTests(unittest.TestCase):
    def test_required_image_files_exist(self):
        required = [
            ".dockerignore",
            "images/vllm-h200/Dockerfile",
            "images/vllm-h200/Dockerfile.snupi-base-fallback",
            "images/vllm-h200/serve-vllm.sh",
            "images/osworld-eval/Dockerfile",
            "images/osworld-eval/run-osworld-eval.sh",
            "scripts/images/build_with_buildkit.sh",
            "scripts/images/smoke_vllm_image.sh",
            "scripts/images/smoke_osworld_eval_image.sh",
            "docs/reproducible-images.md",
        ]
        for rel in required:
            self.assertTrue((ROOT / rel).exists(), rel)

    def test_dockerignore_excludes_generated_state(self):
        text = (ROOT / ".dockerignore").read_text()
        for pattern in [".omx/", "external/", "runs/", ".cache/", "*.log", ".env"]:
            self.assertIn(pattern, text)

    def test_shell_scripts_parse(self):
        scripts = [
            "images/vllm-h200/serve-vllm.sh",
            "images/osworld-eval/run-osworld-eval.sh",
            "scripts/images/build_with_buildkit.sh",
            "scripts/images/smoke_vllm_image.sh",
            "scripts/images/smoke_osworld_eval_image.sh",
            "scripts/run_sample_eval.sh",
        ]
        for rel in scripts:
            subprocess.run(["bash", "-n", str(ROOT / rel)], check=True)

    def test_serving_script_has_required_gates(self):
        text = (ROOT / "images/vllm-h200/serve-vllm.sh").read_text()
        for token in ["TENSOR_PARALLEL_SIZE", "RESERVATION_NVME_ROOT", "/dev/shm", "HF_TOKEN", "--gdn-prefill-backend triton"]:
            self.assertIn(token, text)

    def test_eval_script_serializes_vm_download_and_bounds_tokens(self):
        text = (ROOT / "images/osworld-eval/run-osworld-eval.sh").read_text()
        for token in [
            "ensure_docker_vm_image",
            "zipfile.ZipFile",
            "Removing corrupt/incomplete OSWorld VM archive",
            'export QWEN36_MAX_TOKENS="${QWEN36_MAX_TOKENS:-2048}"',
        ]:
            self.assertIn(token, text)


if __name__ == "__main__":
    unittest.main()
