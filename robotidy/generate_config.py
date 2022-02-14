import sys
from typing import Dict, List, Optional, Set
from pathlib import Path
from textwrap import dedent

import questionary

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


class TransformerConfig:
    def __init__(self, name: str, enabled: bool, msg):
        self.name = name
        self.enabled = enabled
        self.value = None
        self.msg = dedent(msg)
        self.parameters = []
        self.ask()

    def ask(self):
        print("-" * 100)
        questionary.print(f"{self.name} transformer\n")
        answer = questionary.confirm(self.msg + "\n\nDo you want to enable this transformer?", default=True).ask()
        if answer != self.enabled:
            self.value = answer
            self.enabled = answer

    def __str__(self):
        s = f'\n    "{self.name}: enabled = {self.enabled}",' if self.value is not None else ""
        if self.enabled:
            s += "".join(f'\n    "{self.name}: {param}",' for param in self.parameters if param.value is not None)
        return s


class Parameter:
    def __init__(self, question, param):
        self.question = dedent(question)
        self.param = param
        self.value = None
        self.ask()

    def ask(self):
        raise NotImplementedError()

    @staticmethod
    def validate_not_interrupted(value):
        if value is None:
            sys.exit(0)

    def __str__(self):
        return f"{self.param} = {self.value}"


class ParameterBool(Parameter):
    def __init__(self, question: str, param: str, default: bool, first: str, second: str):
        self.default = default
        self.first = first
        self.second = second
        super().__init__(question, param)

    def ask(self):
        answer = questionary.select(
            self.question, default=f"{self.first} (default)", choices=[f"{self.first} (default)", self.second]
        ).ask()
        self.validate_not_interrupted(answer)
        if answer == self.second:
            self.value = not self.default


class ParameterInt(Parameter):
    def __init__(self, question: str, param: str, default: Optional[int], min: int = None, max: int = None):
        self.default = default
        self.min = min
        self.max = max
        super().__init__(question, param)

    def ask(self):
        answer = questionary.text(
            self.question, default=str(self.default), validate=lambda text: validate_int(text, self.min, self.max)
        ).ask()
        self.validate_not_interrupted(answer)
        if answer != str(self.default):
            self.value = int(answer)


class ParameterOrder(Parameter):
    def __init__(self, question: str, param: str, default: str, valid: List, use_all: bool = False):
        self.default = default
        self.valid = valid
        self.use_all = use_all
        super().__init__(question, param)

    def ask(self):
        answer = questionary.text(
            self.question, default=self.default, validate=lambda text: validate_order(text, self.valid, self.use_all)
        ).ask()
        self.validate_not_interrupted(answer)
        if answer != self.default:
            self.value = answer


class ParameterChoice(Parameter):
    def __init__(self, question: str, param: str, default: str, choices: Dict):
        self.default = default
        self.choices = choices
        super().__init__(question, param)

    def ask(self):
        answer = questionary.select(self.question, choices=list(self.choices.keys())).ask()
        self.validate_not_interrupted(answer)
        if self.choices[answer] != self.default:
            self.value = self.choices[answer]


class ParameterSelectSingle(Parameter):
    def __init__(self, question: str, param: str, default: str, choices: Dict):
        self.default = default
        self.choices = choices
        super().__init__(question, param)

    def ask(self):
        answer = questionary.select(self.question, default=self.default, choices=list(self.choices.keys())).ask()
        self.validate_not_interrupted(answer)
        if answer and answer != self.default:
            self.value = self.choices[answer]


class ParameterSelectMany(Parameter):
    def __init__(self, question: str, param: str, default: Set, choices: Dict, select_all: bool = False):
        self.choices = choices
        self.default = default
        self.select_all = select_all
        super().__init__(question, param)

    def ask(self):
        if self.select_all:
            choices = [questionary.Choice(name, checked=True) for name in self.choices]
        else:
            choices = list(self.choices)
        answer = questionary.checkbox(self.question, choices=choices).ask()
        self.validate_not_interrupted(answer)
        selected = {self.choices[ans] for ans in answer}
        if selected and selected != self.default:
            self.value = ",".join(selected)


def validate_int(text, min_val, max_val):
    try:
        value = int(text)
        if min_val is not None:
            if value < min_val:
                return f"Provided number lower than {min_val}"
        if max_val is not None:
            if value > max_val:
                return f"Provided number higher than {max_val}"
        return True
    except ValueError:
        return "Please enter a integer"


def validate_order(text, valid, use_all):
    if not text:
        return f"Use one of: {','.join(valid)}"
    if not use_all and not text:
        return True
    for name in text.split(","):
        if name not in valid:
            return f"{name} not recognized. Use one of: {','.join(valid)}"
    if use_all:
        if sorted(valid) != sorted(text.split(",")):
            return f"Use everything from: {', '.join(valid)}"
    return True
