from collections import defaultdict

from robot.api.parsing import ModelTransformer, Token
from robot.parsing.model import Statement

from robotidy.utils import node_outside_selection, round_to_four, tokens_by_lines, left_align, is_blank_multiline
from robotidy.exceptions import InvalidParameterValueError


class AlignVariablesSection(ModelTransformer):
    """
    Align variables in *** Variables *** section to columns.

    Following code:

        *** Variables ***
        ${VAR}  1
        ${LONGER_NAME}  2
        &{MULTILINE}  a=b
        ...  b=c

    will be transformed to:

        *** Variables ***
        ${VAR}          1
        ${LONGER_NAME}  2
        &{MULTILINE}    a=b
        ...             b=c

    You can configure how many columns should be aligned to longest token in given column. The remaining columns
    will use fixed length separator length ``--spacecount``. By default only first two columns are aligned.
    To align first three columns:

       robotidy --transform AlignVariablesSection:up_to_column=3

    To align all columns set ``up_to_column`` to 0.

    Supports global formatting params: ``--startline`` and ``--endline``.

    See https://robotidy.readthedocs.io/en/latest/transformers/AlignVariablesSection.html for more examples.
    """

    def __init__(self, up_to_column: int = 2, skip_types: str = "", min_width: int = None):
        self.up_to_column = up_to_column - 1
        self.min_width = min_width
        self.skip_types = self.parse_skip_types(skip_types)

    def parse_skip_types(self, skip_types):
        allow_types = {"dict": "&", "list": "@", "scalar": "$"}
        ret = set()
        if not skip_types:
            return ret
        for skip_type in skip_types.split(","):
            if skip_type not in allow_types:
                raise InvalidParameterValueError(
                    self.__class__.__name__,
                    "skip_type",
                    skip_type,
                    "Variable types should be provided in comma separated list:\nskip_type=dict,list,scalar",
                )
            ret.add(allow_types[skip_type])
        return ret

    def generate_config(self):
        from robotidy.generate_config import TransformerConfig, ParameterInt, ParameterSelectMany

        config = TransformerConfig(
            name=self.__class__.__name__,
            enabled=self.__dict__.get("ENABLED", True),
            msg="""
            Do you want to align variables in *** Variables *** section to columns?
            Following code:

                *** Variables ***
                ${VAR}  1
                ${LONGER_NAME}  2
                &{MULTILINE}  a=b
                ...  b=c

            will be transformed to::

                *** Variables ***
                ${VAR}          1
                ${LONGER_NAME}  2
                &{MULTILINE}    a=b
                ...             b=c
            """,
        )
        if not config.enabled:
            return config
        up_to_param = ParameterInt(
            "By default only first 2 data columns are aligned. The rest is separated by standard separator.\n"
            "You can configure how many data columns are aligned (use 0 to align all columns):",
            param="up_to_column",
            default=2,
            min=0,
        )
        skip_types = ParameterSelectMany(
            """
            It is possible to not align variables of given types. You can choose between following types: 
            `scalar` (`$`), `list` (`@`), `dict` (`&`). Invalid variables - such as missing values or not 
            left aligned - will be always aligned no matter the type. You can configure what variable types to skip 
            (none by default):
            """,
            param="skip_types",
            default=set(),
            choices={"scalar (${variable)": "scalar", "dict (&{variable)": "dict", "list (@{variable)": "list"},
        )
        min_width = ParameterInt(
            "Data columns are aligned to longest token in given column. You can change this behaviour and use fixed "
            "minimal width of column. Use 0 for default behaviour (align to longest token):",
            param="min_width",
            default=0,
            min=0,
        )
        config.parameters.append(up_to_param)
        config.parameters.append(skip_types)
        config.parameters.append(min_width)
        return config

    def should_parse(self, node):
        if not node.name:
            return True
        return node.name[0] not in self.skip_types

    def visit_VariableSection(self, node):  # noqa
        if node_outside_selection(node, self.formatting_config):
            return node
        statements = []
        for child in node.body:
            if node_outside_selection(child, self.formatting_config):
                statements.append(child)
            elif child.type in (Token.EOL, Token.COMMENT):
                statements.append(left_align(child))
            elif self.should_parse(child):
                statements.append(list(tokens_by_lines(child)))
            else:
                statements.append(child)
        nodes_to_be_aligned = [st for st in statements if isinstance(st, list)]
        if not nodes_to_be_aligned:
            return node
        look_up = self.create_look_up(nodes_to_be_aligned)  # for every col find longest value
        node.body = self.align_rows(statements, look_up)
        return node

    def align_rows(self, statements, look_up):
        aligned_statements = []
        for st in statements:
            if not isinstance(st, list):
                aligned_statements.append(st)
                continue
            aligned_statement = []
            for line in st:
                if is_blank_multiline(line):
                    line[-1].value = line[-1].value.lstrip(" \t")  # normalize eol from '  \n' to '\n'
                    aligned_statement.extend(line)
                    continue
                up_to = self.up_to_column if self.up_to_column != -1 else len(line) - 2
                for index, token in enumerate(line[:-2]):
                    aligned_statement.append(token)
                    separator = self.calc_separator(index, up_to, token, look_up)
                    aligned_statement.append(Token(Token.SEPARATOR, separator))
                last_token = line[-2]
                # remove leading whitespace before token
                last_token.value = last_token.value.strip() if last_token.value else last_token.value
                aligned_statement.append(last_token)
                aligned_statement.append(line[-1])  # eol
            aligned_statements.append(Statement.from_tokens(aligned_statement))
        return aligned_statements

    def calc_separator(self, index, up_to, token, look_up):
        if index < up_to:
            if self.min_width:
                return max(self.min_width - len(token.value), self.formatting_config.space_count) * " "
            return (look_up[index] - len(token.value) + 4) * " "
        else:
            return self.formatting_config.space_count * " "

    def create_look_up(self, statements):
        look_up = defaultdict(int)
        for st in statements:
            for line in st:
                up_to = self.up_to_column if self.up_to_column != -1 else len(line)
                for index, token in enumerate(line[:up_to]):
                    look_up[index] = max(look_up[index], len(token.value))
        return {index: round_to_four(length) for index, length in look_up.items()}
