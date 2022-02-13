import sys
from pathlib import Path
from textwrap import dedent

from robotidy.transformers import load_transformers


class GenerateConfig:
    @staticmethod
    def collect_config():
        transformers = load_transformers(None, {}, allow_disabled=True)
        return [
            transformer.generate_config() for transformer in transformers if hasattr(transformer, "generate_config")
        ]

    def generate(self):
        configs = self.collect_config()
        config_list = "".join(str(transformer) for transformer in configs)
        if not config_list:
            return
        toml_file = f"""[tool.robotidy]\nconfigure = [{config_list}\n]"""
        dest = Path("pyproject_robotidy.toml")
        with open(dest, "w") as f:
            f.write(toml_file)
        print(f"Saved configuration file in {dest.resolve()}")


class TransformerGenConfig:
    def __init__(self, name: str, enabled: bool, msg):
        self.name = name
        self.enabled = enabled
        self.value = None
        self.msg = msg
        self.parameters = []
        self.ask()

    def ask(self):
        print("-" * 100)
        print(f"\n{self.name} transformer")
        print(dedent(self.msg))
        print("1) Yes (default)" if self.enabled else "1) No (default)")
        print("2) No" if self.enabled else "2) Yes")
        print("3) Exit")
        answer = ValidateInt(min=1, max=3).parse()
        if answer == 3:
            sys.exit(0)
        if answer == 2:
            self.value = self.enabled = not self.enabled

    def __str__(self):
        s = f'\n    "{self.name}: enabled = {self.enabled}",' if self.value is not None else ""
        if self.enabled:
            s += "".join(f'\n    "{self.name}: {param}",' for param in self.parameters if param.value is not None)
        return s


class Parameter:
    def __init__(self, question: str, param: str, validate_method):
        self.question = question
        self.param = param
        self.value = None
        self.validate_method = validate_method
        self.ask()

    def ask(self):
        print(f"\n{self.param} parameter")
        print(dedent(self.question))
        print("1) Use default")
        print("2) Configure it")
        print("3) Exit")
        if not true_false_exit():
            return
        print("Provide new value:")
        self.value = self.validate_method.parse()

    def __str__(self):
        return f"{self.param} = {self.value}"


class ParameterBool:
    def __init__(self, question: str, param: str, default: bool, first: str, second: str):
        self.question = question
        self.param = param
        self.value = None
        self.default = default
        self.first = first
        self.second = second
        self.ask()

    def ask(self):
        print()
        print(self.question)
        print(f"1) {self.first} (default)")
        print(f"2) {self.second}")
        print("3) Exit")
        if true_false_exit():
            self.value = not self.default

    def __str__(self):
        return f"{self.param} = {self.value}"


def true_false_exit():
    answer = ValidateInt(min=1, max=3).parse()
    if answer == 3:
        sys.exit(0)
    return answer == 2


class GetValue:
    def get_value(self):
        return input("Your answer: ")


class ValidateInt(GetValue):
    def __init__(self, min: int = None, max: int = None):
        self.min = min
        self.max = max

    def parse(self):
        for retry in range(3):
            try:
                value_int = int(self.get_value())
                if self.min is not None:
                    if value_int < self.min:
                        print(f"Provided number lower than {self.min}")
                        continue
                if self.max is not None:
                    if value_int > self.max:
                        print(f"Provided number higher than {self.min}")
                        continue
                return value_int
            except ValueError:
                print("Provided answer is not integer")
                continue
        else:
            print("Failed to get valid value. Exiting..")
            sys.exit(0)
