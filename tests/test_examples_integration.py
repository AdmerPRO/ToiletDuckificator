import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from toiletduckificator.obfuscator import obfuscate_path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _run_python(script_path: Path, *, cwd: Path) -> str:
    completed = subprocess.run(
        [sys.executable, script_path.name],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=True,
    )
    return completed.stdout


class TestExampleIntegrations(unittest.TestCase):
    def test_obfuscated_single_file_example_runs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_file = Path(tmp_dir) / "sample_app.duck.py"
            obfuscate_path(REPO_ROOT / "example_program" / "sample_app.py", output_file)

            stdout = _run_python(output_file, cwd=output_file.parent)

            self.assertEqual(
                stdout,
                "{'total': 108, 'average': 18, 'high_scores': [8, 15, 16, 23, 42], 'indexed_count': 6}\n"
                "{'mode': 'demo', 'retry_budget': 5, 'members': ['Ada', 'Bob', 'Cy']}\n"
                "35\n"
                "70\n",
            )

    def test_obfuscated_flat_folder_example_runs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_root = Path(tmp_dir) / "example_folder_program_duckified"
            obfuscate_path(REPO_ROOT / "example_folder_program", output_root)

            stdout = _run_python(output_root / "main.py", cwd=output_root)

            self.assertEqual(stdout, "Toilet Duckificator: total=109, count=5, high=3, highest=31\n")

    def test_obfuscated_nested_folder_example_runs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_root = Path(tmp_dir) / "example_nested_program_duckified"
            obfuscate_path(REPO_ROOT / "example_nested_program", output_root)

            stdout = _run_python(output_root / "main.py", cwd=output_root)

            self.assertEqual(stdout, "[ NESTED TOILET DUCKIFICATOR RUNNING ON V2 ]\n")


if __name__ == "__main__":
    unittest.main()
