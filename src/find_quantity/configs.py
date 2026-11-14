import logging
from dataclasses import dataclass, fields
from pathlib import Path


logger = logging.getLogger("find_quantity.cli")


@dataclass
class Config:
    PROJECT_FOLDER: Path = Path.home() / "find_quantities"
    RAW_PRODUCTS_DATA: Path = PROJECT_FOLDER / "produits.csv"
    RAW_SHOWROOMS_DATA: Path = PROJECT_FOLDER / "showrooms.csv"
    STEP_ONE_TRANSFORM_PATH: Path = PROJECT_FOLDER / "output" / "1-Transform"
    STEP_TWO_CALCULATE_PATH: Path = PROJECT_FOLDER / "output" / "2-Calculate"
    STEP_THREE_VALIDATE_PATH: Path = PROJECT_FOLDER / "output" / "3-Validate"
    MERGE_CONFIG_PATH: Path = PROJECT_FOLDER / "product_merge_rules.yml"
    HOLIDAYS_PATH: Path = PROJECT_FOLDER / "holidays.yml"
    CAISSE_PATH: Path = PROJECT_FOLDER / "caisse.csv"
    CLEAN_BEFORE_EACH_RUN: bool = True
    CSV_SEPERATOR: str = ";"
    IN_ENCODING: str = "cp1252"
    OUT_ENCODING: str = "utf-8"
    YEAR: int = 2026  # Changed with -y via cli arg

    def create_folders(self):
        for attr in fields(self):
            path_v = self.__getattribute__(attr.name)
            if isinstance(path_v, Path):
                if not path_v.suffix and not path_v.exists():
                    path_v.mkdir(exist_ok=True, parents=True)
                    logger.info(f"Creating folder {path_v} ...")

    def clean_up(self):
        for dir in [
            self.STEP_ONE_TRANSFORM_PATH,
            self.STEP_TWO_CALCULATE_PATH,
            self.STEP_THREE_VALIDATE_PATH,
        ]:
            if dir.exists():
                [f.unlink() for f in dir.glob("*")]

    def _copy_template(self, template_name: str, destination: Path):
        import importlib.resources
        import shutil
        import find_quantity

        package_files = importlib.resources.files(find_quantity)
        template = package_files / "templates" / template_name
        if not destination.exists():
            shutil.copy(template, destination)

    def copy_merge_configs(self):
        self._copy_template("product_merge_rules.yml", self.MERGE_CONFIG_PATH)

    def copy_holidays_config(self):
        self._copy_template("holidays.yml", self.HOLIDAYS_PATH)


config = Config()
