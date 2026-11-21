# Find Quantity

Program to help determine quantity of products for each Showroom.

## Setup
Follow the steps to install the software
* Install [Python](https://www.python.org/downloads/).
* Install [git](https://git-scm.com/downloads)
* Open `PowerShell` from windows start menu
* run `python --version` to confirm python is installed
* run `git --version` to confirm git is installed
* Make sure pip is installed. `pip --version`
* Create a new folder using the command `mkdir bin`
* Change to the newly created folder `cd bin`
* Create a virtual enviroment for python application `python -m venv venv`
* Activate the virtual enviroment `.\venv\Scripts\activate`
* Install package from repo: `pip install git+https://github.com/etdabenzeghiba-lgtm/zin_Find_quantities.git`


## Update
With the new version, run `find_quantity -u` to automatically update.

Alternatively, manual updating is supported via the steps below:
* Open `PowerShell` from windows start menu
* Change to the folder `cd bin`
* Activate the virtual enviroment `.\venv\Scripts\activate`
* Run the command to update: `pip install git+https://github.com/etdabenzeghiba-lgtm/zin_Find_quantities.git`


## Usage
To use the program follow these steps below
* Open a `PowerShell` window from windows start menu
* Change to the folder `cd bin`
* Activate the virtual enviroment `.\venv\Scripts\activate`
* Run the command `find_quantity` and follow the instructions (if it doesn't work run `python -m find_quantity`)


### How to change the year?
* Run the command `find_quantity -y 2023`


### Flags/Options
* `-h`: display the help menu
* `-v`: prints out the software version
* `-u`: perform update of the software to the latest version in the repo
* `-y YEAR`: specify the year of the data for the final date generation. The default is 2026.
* `-e ENCODING`: specify type of encodin. the default is latin-1


## Cash rules: CCP and espece (`caisse.csv`)
The program creates an empty `caisse.csv` in the project folder. Fill it with one row per money movement:

```
mois;showroom;Code-Showroom;mode;date;montant
1;Alger;SH01;CCP;2026-01-20;500000
1;Oran;SH02;espece;2026-01-08;12000
1;Oran;SH02;espece;2026-01-15;8000
```

* `mode` is `CCP` or `espece`. A showroom has ONE mode per month (mixing them is refused).
* **CCP**: all the tickets de caisse are dated strictly BEFORE the date of the encaissement.
* **espece**: each row is a daily cash expense. On its date, the sales so far (that day included)
  must cover all the expenses so far. If the equal split over the days can't do it, the program puts
  more sales in the first days, just enough to pay the expenses on their dates. If the expenses are
  higher than all the sales, a warning names the date that fails. The amounts are compared with the sales total without taxes (`Total`).
* Dates: `YYYY-MM-DD` (or `DD/MM/YYYY`). Amounts: `1234.50` or `1234,50`.
* A showroom missing from the file gets no rule (a warning is shown).
* Results, in `output/3-Validate`: `daily_sales_CCP.csv` and `daily_sales_ESPECE.csv` (separate etats,
  never mixed). Showrooms missing from `caisse.csv` go to `daily_sales_sans_mode.csv`.
  If `caisse.csv` is empty, the usual single `daily_sales.csv` is kept.


## Big files (more than one Excel sheet)
Excel shows at most 1,048,576 rows per sheet. If a daily sales file has more than 1,000,000 data rows
(`EXCEL_MAX_ROWS_PER_SHEET` in `configs.py`), the program writes it as an Excel file
(`daily_sales_CCP.xlsx`, for example) with several sheets `Feuil1`, `Feuil2`, ... Each sheet is filled,
then the next one is started, and each sheet keeps the header line. The `.csv` file is then removed.
Smaller files stay as `.csv`.


## Selling days and holidays
The daily distribution now covers **every day of the month**, up to the last day (28, 29, 30 or 31).
Fridays are always skipped. Holidays are skipped too: they are listed in the file `holidays.yml`,
created automatically in the project folder (next to `product_merge_rules.yml`).
* One date per line, format `- YYYY-MM-DD`.
* The file contains the holidays of 2026 and 2027. The religious dates of 2027 are estimates:
  correct them when the official dates are announced, and add new years when needed.
* If a year has no holidays in the file, a warning is shown and only Fridays are skipped.
* To get the new default list, delete your `holidays.yml` and run the program again.

## Merge Rules
The program offer different ways to merge the products together as package. A template file is automatically
created at the start of new project. In order to work effectively with the config `merge_product_rules.yml`,
there  are few rules to keep in mind:
* The YAML (`.yml`) is sensitve to indentations and white spaces.
* The structure of the file sections must be followed as specified in the default template.
* The available commads are:
    1. `AutoMergeIOProducts`: auto merge all products tags (`n_article`) ending with `-I` or `-O`
    2. `CombineProducts`: takes a list of products under the section `packages` and merge them together
    3. `MergeBasedOnPattern`: search for products tags (`n_article`) matching the regex `pattern` and
       combines them with the `products` section under `packages`. Multiple `packages` with one or
        more `products` can be defined at the same time.

**WARNING**: Special attention must be paid to the `pattern` to avoid matching against the wrong products.
For pattern testing, the website [regex](https://regexr.com/) is very useful.



## Issues
### `find_quantity` not found
After following the steps to install the program, there's no error at this stage, but when you run try to run the program using `find_quantity` you get an error. Try to run it with `python -m find_quantity` instead. This issue might be due the package has not been added to your `PowerShell` path. This could be due to virtual environment not activated correctly for some reason (venv not showing in green in the command prompt).
