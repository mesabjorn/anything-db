from . import logger


def receive_yes_no(question: str) -> bool:
    """Question user input wiht question then maps result to true or false
    Values considered True : ("true", "1", "t", "y", "yes") (case insensitive)
    Values considered False: ("false", "0", "f", "n", "no") (case insensitive)

    Args:
        question (str): question to ask user on command-line interface

    Returns:
        bool: _description_
    """

    yes_values = ("true", "1", "t", "y", "yes")
    no_values = ("false", "0", "f", "n", "no")

    answer = input(question).lower().strip()
    while True:
        if answer in yes_values or answer in no_values:
            break
        logger.warning(
            f"Answer cannot be mapped to either true or false.\nEnter one of the following values:\n{yes_values}, {no_values}"
        )

    return answer in yes_values
