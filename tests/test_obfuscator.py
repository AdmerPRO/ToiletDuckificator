import ast
import re
import textwrap
import unittest

from toiletduckificator.obfuscator import obfuscate_source


IDENTIFIER_RE = re.compile(r"\b[a-zA-Z_][a-zA-Z0-9_]{15}\b")


class ObfuscatorTests(unittest.TestCase):
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
        self.assertGreaterEqual(len(set(IDENTIFIER_RE.findall(result))), 3)

    def test_does_not_rename_imports_or_attributes(self) -> None:
        source = textwrap.dedent(
            """
            import math

            radius = 5
            area = math.pi * radius * radius
            """
        )

        result = obfuscate_source(source)
        self.assertIn("math.pi", result)
        self.assertIn("import math", result)
        self.assertNotIn(" radius ", " " + result + " ")

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
        self.assertIn("nonlocal", result)
        self.assertIn("global", result)
        self.assertNotIn("total", result)
        self.assertNotIn("flag", result)

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
        self.assertEqual(namespace["build"]([10, 20]), {0: 10, 1: 20})

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
        self.assertEqual(original_ns["make_adder"](5)(7), obfuscated_ns["make_adder"](5)(7))

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


if __name__ == "__main__":
    unittest.main()
