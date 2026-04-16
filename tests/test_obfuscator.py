import ast
import re
import tempfile
import textwrap
import unittest
from pathlib import Path

from toiletduckificator.obfuscator import obfuscate_path, obfuscate_source


IDENTIFIER_RE = re.compile(r"\b[a-zA-Z_][a-zA-Z0-9_]{15}\b")
FUNCTION_RE = re.compile(r"\b[a-zA-Z_][a-zA-Z0-9_]{23}\b")
MODULE_FILE_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]{7}\.py$")


def _user_callables(namespace: dict[str, object]) -> list[object]:
    return [
        value
        for key, value in namespace.items()
        if key != "__builtins__"
        and not key.startswith("_duck_")
        and not (key.startswith("_") and len(key) <= 2)
        and callable(value)
        and getattr(value, "__module__", None) is None
    ]


def _user_values(namespace: dict[str, object]) -> dict[str, object]:
    return {
        key: value
        for key, value in namespace.items()
        if key != "__builtins__" and not key.startswith("_duck_") and not (key.startswith("_") and len(key) <= 2)
    }


def _user_data_values(namespace: dict[str, object]) -> list[object]:
    return [value for value in _user_values(namespace).values() if not callable(value)]


class TestObfuscator(unittest.TestCase):
    def test_renames_module_and_function_variables(self) -> None:
        source = textwrap.dedent(
            """
            counter = 3

            def compute(value):
                local_total = value + counter
                return local_total
            """
        )

        result = obfuscate_source(source)
        self.assertNotIn("counter", result)
        self.assertNotIn("local_total", result)
        self.assertNotIn("compute", result)
        self.assertIn("b85decode", result)
        namespace: dict[str, object] = {}
        exec(result, namespace)
        self.assertGreaterEqual(len(_user_values(namespace)), 2)

    def test_does_not_rename_imports_or_attributes(self) -> None:
        source = textwrap.dedent(
            """
            import math

            radius = 5
            area = math.pi * radius * radius
            """
        )

        namespace: dict[str, object] = {}
        exec(obfuscate_source(source), namespace)
        values = _user_data_values(namespace)
        self.assertIn(5, values)
        self.assertIn(25 * 3.141592653589793, values)

    def test_handles_global_and_nonlocal(self) -> None:
        source = textwrap.dedent(
            """
            flag = 1

            def outer():
                total = 2

                def inner():
                    nonlocal total
                    global flag
                    total += flag
                    return total

                return inner()
            """
        )

        result = obfuscate_source(source)
        self.assertNotIn("total", result)
        self.assertNotIn("flag", result)
        namespace: dict[str, object] = {}
        exec(result, namespace)
        outer = _user_callables(namespace)[0]
        self.assertEqual(outer(), 3)

    def test_handles_comprehensions_and_walrus(self) -> None:
        source = textwrap.dedent(
            """
            items = [1, 2, 3]

            def build():
                return [(temp := value * 2) for value in items if temp > 2]
            """
        )

        result = obfuscate_source(source)
        self.assertNotIn("temp", result)
        self.assertNotIn("value", result)
        self.assertNotIn("items", result)

    def test_dict_comprehension_uses_outer_scope_iterable(self) -> None:
        source = textwrap.dedent(
            """
            def build(values):
                indexed = {index: value for index, value in enumerate(values)}
                return indexed
            """
        )

        namespace: dict[str, object] = {}
        exec(obfuscate_source(source), namespace)
        build = _user_callables(namespace)[0]
        self.assertEqual(build([10, 20]), {0: 10, 1: 20})

    def test_preserves_runtime_behavior(self) -> None:
        source = textwrap.dedent(
            """
            base = 10

            def make_adder(amount):
                def inner(value):
                    return amount + value + base
                return inner

            result = make_adder(5)(7)
            """
        )

        original_ns: dict[str, object] = {}
        obfuscated_ns: dict[str, object] = {}
        exec(source, original_ns)
        exec(obfuscate_source(source), obfuscated_ns)
        obfuscated_function = _user_callables(obfuscated_ns)[0]
        self.assertEqual(original_ns["make_adder"](5)(7), obfuscated_function(5)(7))

    def test_output_is_valid_python(self) -> None:
        source = textwrap.dedent(
            """
            class Example:
                size = 4

                def method(self, amount):
                    temp_value = amount + self.size
                    return temp_value
            """
        )

        result = obfuscate_source(source)
        ast.parse(result)

    def test_obfuscates_int_literals_to_bytes(self) -> None:
        source = textwrap.dedent(
            """
            value = 513
            negative = -7
            """
        )

        result = obfuscate_source(source)
        self.assertNotIn("= 513", result)
        self.assertNotIn("= -7", result)
        namespace: dict[str, object] = {}
        exec(result, namespace)
        self.assertEqual(sorted(_user_data_values(namespace)), [-7, 513])

    def test_obfuscates_strings_inside_data_literals(self) -> None:
        source = textwrap.dedent(
            """
            payload = {"message": "duck", "items": ["alpha", "beta"]}
            """
        )

        namespace: dict[str, object] = {}
        exec(obfuscate_source(source), namespace)
        payload_key = next(key for key, value in _user_values(namespace).items() if not callable(value))
        self.assertEqual(
            namespace[payload_key],
            {"message": "duck", "items": ["alpha", "beta"]},
        )

    def test_minifies_simple_function_blocks_to_single_line(self) -> None:
        source = textwrap.dedent(
            """
            def build():
                return 42
            """
        )

        result = obfuscate_source(source)
        self.assertNotIn("\n\n\n", result)
        self.assertIn("b85decode", result)

    def test_renames_function_definitions_to_24_characters(self) -> None:
        source = textwrap.dedent(
            """
            def helper():
                return 1

            def call_helper():
                return helper()
            """
        )

        result = obfuscate_source(source)
        self.assertNotIn("helper", result)
        self.assertNotIn("call_helper", result)
        namespace: dict[str, object] = {}
        exec(result, namespace)
        self.assertEqual(len(_user_callables(namespace)), 2)

    def test_aliases_common_builtins(self) -> None:
        source = textwrap.dedent(
            """
            def build(values):
                return sum(values) + len(values)
            """
        )

        result = obfuscate_source(source)
        self.assertNotIn("sum(", result)
        namespace: dict[str, object] = {}
        exec(result, namespace)
        build = _user_callables(namespace)[0]
        self.assertEqual(build([1, 2, 3]), 9)

    def test_folder_obfuscation_renames_nested_paths_and_updates_imports(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            source_root = Path(tmp_dir) / "source"
            output_root = Path(tmp_dir) / "output"
            source_root.mkdir()
            (source_root / "services").mkdir()
            (source_root / "services" / "helpers").mkdir()

            (source_root / "main.py").write_text(
                textwrap.dedent(
                    """
                    from services.report_builder import build_report
                    from settings import APP_NAME

                    def run():
                        return build_report(APP_NAME)


                    if __name__ == "__main__":
                        print(run())
                    """
                ).strip()
                + "\n",
                encoding="utf-8",
            )
            (source_root / "services" / "__init__.py").write_text("", encoding="utf-8")
            (source_root / "services" / "helpers" / "__init__.py").write_text("", encoding="utf-8")
            (source_root / "services" / "report_builder.py").write_text(
                textwrap.dedent(
                    """
                    from services.helpers.message_tools import build_message

                    def build_report(name):
                        return build_message(name)
                    """
                ).strip()
                + "\n",
                encoding="utf-8",
            )
            (source_root / "services" / "helpers" / "message_tools.py").write_text(
                textwrap.dedent(
                    """
                    def build_message(name):
                        return f"Hello, {name}!"
                    """
                ).strip()
                + "\n",
                encoding="utf-8",
            )
            (source_root / "settings.py").write_text('APP_NAME = "Duck"\n', encoding="utf-8")

            results = obfuscate_path(source_root, output_root)

            self.assertEqual(len(results), 6)
            output_relative_paths = sorted(result.output_path.relative_to(output_root) for result in results)
            output_names = [path.name for path in output_relative_paths]

            self.assertIn("main.py", output_names)
            self.assertNotIn("settings.py", output_names)
            self.assertNotIn("report_builder.py", output_names)
            self.assertNotIn("message_tools.py", output_names)

            for path in output_relative_paths:
                if path.name not in {"main.py", "__init__.py"}:
                    self.assertRegex(path.name, MODULE_FILE_RE.pattern)

            nested_directories = {path.parent for path in output_relative_paths if path.parent != Path(".")}
            self.assertTrue(nested_directories)
            for directory in nested_directories:
                for part in directory.parts:
                    self.assertRegex(part, r"^[a-zA-Z_][a-zA-Z0-9_]{7}$")

            output_sources = "\n".join(result.output_path.read_text(encoding="utf-8") for result in results)
            self.assertNotIn("from services.report_builder import", output_sources)
            self.assertNotIn("from services.helpers.message_tools import", output_sources)
            self.assertNotIn("from settings import", output_sources)
            self.assertIn("b85decode", output_sources)

    def test_obfuscates_private_methods_and_attributes(self) -> None:
        source = textwrap.dedent(
            """
            class Example:
                def __init__(self):
                    self._value = 4

                def _hidden(self):
                    return self._value + 1

            result = Example()._hidden()
            """
        )

        result = obfuscate_source(source)
        self.assertNotIn("_hidden", result)
        self.assertNotIn("_value", result)
        namespace: dict[str, object] = {}
        exec(result, namespace)
        self.assertIn(5, _user_data_values(namespace))


if __name__ == "__main__":
    unittest.main()
