import find_quantity.configs as C
from find_quantity.cli import CliArgs, wrap
from find_quantity.commands import (
    CalculateDroitDeTimbre,
    CalculateQuantitiesCommand,
    DevideProductToSellingDays,
    ProcessFilesCommand,
    SetupFolderStructure,
    SplitDailySalesByMode,
    DevideProductBonDeMoument,
)
from find_quantity.utils.logs import logger, logging

file_logger = logging.getLogger("find_quantity")


WELCOME_MESSAGE = f"""
{"*" * 30}
Find Showrooms Quantity
{"*" * 30}
"""


def main() -> None:
    logger.info(WELCOME_MESSAGE)
    try:
        CliArgs().parse_args()
        SetupFolderStructure().execute()
        ProcessFilesCommand().execute()
        CalculateQuantitiesCommand().execute()
        DevideProductBonDeMoument().execute()
        DevideProductToSellingDays().execute()
        CalculateDroitDeTimbre().execute()
        SplitDailySalesByMode().execute()
        logger.info("Finished!")
    except FileNotFoundError as e:
        file_logger.exception(e)
        logger.error(
            wrap(
                f"Make sure you have data in the input files {C.config.RAW_SHOWROOMS_DATA} and {C.config.RAW_PRODUCTS_DATA}"
            )
        )
    except KeyboardInterrupt:
        logger.info("Bye!")

    except Exception as e:
        file_logger.exception(e)
        logger.exception(e)
        logger.info("")

        CliArgs().parser.print_help()


if __name__ == "__main__":
    main()
