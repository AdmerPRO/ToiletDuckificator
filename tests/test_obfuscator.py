import ast
import re
import tempfile
import textwrap
import unittest
from pathlib import Path

from toiletduckificator.obfuscator import ObfuscationOptions, obfuscate_path, obfuscate_source


IDENTIFIER_RE = re.compile(r"\b[a-zA-Z_][a-zA-Z0-9_]{15}\b")
FUNCTION_RE = re.compile(r"\b[a-zA-Z_][a-zA-Z0-9_]{23}\b")
MODULE_FILE_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]{7}\.py$")


def _plain_options(**overrides: object) -> ObfuscationOptions:
    options = {"encrypt_output": False, "minify_output": False}
    options.update(overrides)
    return ObfuscationOptions(**options)


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

    def test_preserves_zero_argument_super_calls(self) -> None:
        source = textwrap.dedent(
            """
            class Base:
                def greet(self):
                    return "base"

            class Child(Base):
                def greet(self):
                    return super().greet()

            result = Child().greet()
            """
        )

        namespace: dict[str, object] = {}
        exec(obfuscate_source(source, options=_plain_options()), namespace)
        self.assertIn("base", _user_data_values(namespace))

    def test_handles_except_handler_bindings(self) -> None:
        source = textwrap.dedent(
            """
            def run(value):
                try:
                    1 / value
                except ZeroDivisionError as err:
                    return str(err)

            result = run(0)
            """
        )

        namespace: dict[str, object] = {}
        exec(obfuscate_source(source, options=_plain_options()), namespace)
        self.assertIn("division by zero", _user_data_values(namespace))

    def test_handles_match_capture_bindings(self) -> None:
        source = textwrap.dedent(
            """
            def run(value):
                match value:
                    case {"x": item}:
                        return item
                    case _:
                        return None

            result = run({"x": 7})
            """
        )

        namespace: dict[str, object] = {}
        exec(obfuscate_source(source, options=_plain_options()), namespace)
        self.assertIn(7, _user_data_values(namespace))

    def test_preserves_literal_match_patterns(self) -> None:
        source = textwrap.dedent(
            """
            def run(value):
                match value:
                    case 1:
                        return "one"
                    case _:
                        return "other"

            result = (run(1), run(2))
            """
        )

        namespace: dict[str, object] = {}
        exec(obfuscate_source(source, options=_plain_options()), namespace)
        self.assertIn(("one", "other"), _user_data_values(namespace))

    def test_keeps_future_imports_ahead_of_generated_helpers(self) -> None:
        source = textwrap.dedent(
            """
            from __future__ import annotations

            class Node:
                next: Node | None = None
            """
        )

        result = obfuscate_source(source, options=_plain_options())
        self.assertTrue(result.lstrip().startswith("from __future__ import annotations"))
        namespace: dict[str, object] = {}
        exec(result, namespace)

    def test_renames_private_members_accessed_through_instance_variables(self) -> None:
        source = textwrap.dedent(
            """
            class Example:
                def __init__(self):
                    self._value = 4

                def _hidden(self):
                    return self._value + 1

            obj = Example()
            result = obj._hidden()
            """
        )

        result = obfuscate_source(source, options=_plain_options())
        self.assertNotIn("_hidden", result)
        self.assertNotIn("_value", result)
        namespace: dict[str, object] = {}
        exec(result, namespace)
        self.assertIn(5, _user_data_values(namespace))

    def test_does_not_treat_staticmethod_arguments_as_current_class_instances(self) -> None:
        source = textwrap.dedent(
            """
            class Example:
                def _secret(self):
                    return 1

                @staticmethod
                def read(value):
                    return value._secret

            class Other:
                def __init__(self):
                    self._secret = 9

            result = Example.read(Other())
            """
        )

        namespace: dict[str, object] = {}
        exec(obfuscate_source(source, options=_plain_options()), namespace)
        self.assertIn(9, _user_data_values(namespace))

    def test_builtin_aliasing_respects_shadowed_names_when_identifier_renaming_is_disabled(self) -> None:
        source = textwrap.dedent(
            """
            def run():
                len = lambda values: 123
                return len([1, 2, 3])

            result = run()
            """
        )

        namespace: dict[str, object] = {}
        exec(
            obfuscate_source(
                source,
                options=_plain_options(rename_identifiers=False),
            ),
            namespace,
        )
        self.assertIn(123, _user_data_values(namespace))

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

    def test_can_disable_literal_obfuscation_and_encryption(self) -> None:
        source = 'value = 513\nlabel = "duck"\n'

        result = obfuscate_source(
            source,
            options=ObfuscationOptions(
                obfuscate_literals=False,
                encrypt_output=False,
                minify_output=False,
            ),
        )

        self.assertIn("513", result)
        self.assertIn("duck", result)
        self.assertNotIn("b85decode", result)

    def test_can_disable_module_renaming_for_folders(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            source_root = Path(tmp_dir) / "source"
            output_root = Path(tmp_dir) / "output"
            source_root.mkdir()
            (source_root / "pkg").mkdir()
            (source_root / "main.py").write_text("from pkg.helper import build\n", encoding="utf-8")
            (source_root / "pkg" / "__init__.py").write_text("", encoding="utf-8")
            (source_root / "pkg" / "helper.py").write_text("def build():\n    return 1\n", encoding="utf-8")

            results = obfuscate_path(
                source_root,
                output_root,
                options=ObfuscationOptions(rename_modules=False),
            )

            output_relative_paths = sorted(result.output_path.relative_to(output_root) for result in results)
            self.assertIn(Path("main.py"), output_relative_paths)
            self.assertIn(Path("pkg", "__init__.py"), output_relative_paths)
            self.assertIn(Path("pkg", "helper.py"), output_relative_paths)

    def test_single_file_output_path_can_be_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            source_file = Path(tmp_dir) / "script.py"
            output_root = Path(tmp_dir) / "output"
            source_file.write_text("value = 1\n", encoding="utf-8")
            output_root.mkdir()

            results = obfuscate_path(source_file, output_root, options=_plain_options())

            self.assertEqual(results[0].output_path, output_root / "script.py")
            self.assertTrue((output_root / "script.py").exists())

    def test_folder_obfuscation_preserves_dunder_main(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            source_root = Path(tmp_dir) / "package"
            output_root = Path(tmp_dir) / "output"
            source_root.mkdir()
            (source_root / "__init__.py").write_text("", encoding="utf-8")
            (source_root / "__main__.py").write_text('print("duck")\n', encoding="utf-8")

            results = obfuscate_path(source_root, output_root, options=_plain_options())

            output_relative_paths = sorted(result.output_path.relative_to(output_root) for result in results)
            self.assertIn(Path("__main__.py"), output_relative_paths)


if __name__ == "__main__":
    unittest.main()
