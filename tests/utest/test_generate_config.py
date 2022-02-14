from unittest.mock import patch, mock_open
from pathlib import Path

from robotidy.generate_config import GenerateConfig
from robotidy.transformers.AlignVariablesSection import AlignVariablesSection


class TestGenerateConfig:
    def test_generate(self):
        answers = [
            1,  # enable AlignSettingsSection
            2,  # configure up_to_column
            3,  # up_to_column = 3
            2,  # configure argument_indent
            0,  # argument_indent = 0
            1,  # do not configure min_width
            2,  # disable AlignTestCases
            2,  # disable InlineIf
        ] + [
            2
        ] * 100  # disable rest
        expected_config = (
            "[tool.robotidy]\n"
            "configure = [\n"
            '    "AlignSettingsSection: up_to_column = 3",\n'
            '    "AlignSettingsSection: argument_indent = 0",\n'
            '    "AlignTestCases: enabled = False",\n'
            '    "InlineIf: enabled = False",\n'
            "]"
        )
        open_mock = mock_open()
        with patch("builtins.input", side_effect=answers), patch(
            "robotidy.generate_config.open", open_mock, create=True
        ):
            GenerateConfig().generate()
        open_mock.assert_called_with(Path("pyproject_robotidy.toml"), "w")
        open_mock.return_value.write.assert_called_once_with(expected_config)
