# Standard library imports.
from csv import DictReader, DictWriter
from io import BytesIO, StringIO
from os import getenv, makedirs
from pathlib import Path

# Third party imports.
from foundry_sdk import Config, FoundryClient, PalantirRPCException, UserTokenAuth
from foundry_sdk.v1.datasets.models import DatasetRid
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from requests import Session

# Local imports.
from constants import HEATHER_GITLAB_COMMENTS_COLUMNS, HEATHER_GITLAB_STATE_COLUMNS


STATE_INTEGER_COLUMNS = ["gitlab_project_id", "gitlab_iid"]
STATE_LONG_COLUMNS = ["gitlab_issue_id", "gitlab_comment_count"]
STATE_BOOLEAN_COLUMNS = ["heather_managed", "external_key_found"]

COMMENT_INTEGER_COLUMNS = ["gitlab_project_id", "gitlab_iid"]
COMMENT_LONG_COLUMNS = ["gitlab_issue_id", "gitlab_note_id"]
COMMENT_BOOLEAN_COLUMNS = ["is_system", "is_edited"]


class VantageClient:
    def __init__(self, verify: str | bool = False):
        """Builds a client for interacting with Vantage.

        Environment Variables:
          FOUNDRY_HOSTNAME: The FQDN of Vantage. Example: vantage.army.mil.
          FOUNDRY_TOKEN: Vantage API token for the current user or service account.
          FOUNDRY_BRANCH_ID: Dataset branch name. Defaults to master.
        """
        self.hostname = getenv("FOUNDRY_HOSTNAME", getenv("VANTAGE_HOSTNAME", ""))
        self.token = getenv("FOUNDRY_TOKEN", getenv("VANTAGE_TOKEN", ""))
        self.branch_name = getenv("FOUNDRY_BRANCH_ID", "master")
        self.transaction_type = getenv("FOUNDRY_TRANSACTION_TYPE", "SNAPSHOT")
        self.local_gl_issues_csv = getenv("HEATHER_GL_ISSUES_CSV", "")
        self.local_output_directory = getenv("HEATHER_LOCAL_OUTPUT_DIRECTORY", "")
        self.client = self.__build_foundry_client(verify=verify)
        self.session = Session()

        if self.token != "":
            self.session.headers.update({"Authorization": f"Bearer {self.token}"})

    def read_table(self, dataset_rid: DatasetRid | str) -> list[dict]:
        """Reads a Vantage dataset as CSV rows.

        Scarab currently uses the Foundry SDK for writing. Heather keeps this small
        direct read call because the source table must be read as runtime input.
        Local CSV mode is still supported for safe dry-run testing.
        """
        if self.local_gl_issues_csv != "":
            return self.__read_local_csv(file_path=self.local_gl_issues_csv)

        self.__validate_remote_configuration()

        response = self.session.get(
            url=f"{self.__base_url()}/api/v1/datasets/{dataset_rid}/readTable",
            params={"branchId": self.branch_name, "format": "CSV"},
            timeout=120,
        )
        response.raise_for_status()
        return self.__parse_csv(csv_content=response.text)

    def upload_rows(
        self,
        dataset_rid: DatasetRid | str,
        file_path: str,
        columns: list[str],
        rows: list[dict],
    ) -> None:
        """Uploads rows as a typed Parquet snapshot to a Vantage dataset."""
        dataframe = self.__build_typed_dataframe(columns=columns, rows=rows)

        if self.local_output_directory != "":
            csv_content = self.__rows_to_csv(columns=columns, rows=rows)
            self.__write_local_csv(file_path=file_path, csv_content=csv_content)

        self.upload_dataframe_as_parquet_snapshot(
            dataframe=dataframe,
            dataset_rid=dataset_rid,
        )

    def upload_dataframe_as_parquet_snapshot(
        self,
        dataframe: pd.DataFrame,
        dataset_rid: DatasetRid | str,
    ) -> None:
        """Uploads a Pandas dataframe as a Parquet SNAPSHOT.

        Heather's write-back datasets are PySpark-initialized Parquet tables.
        Heather writes full current-state snapshots, so the correct transaction
        type is SNAPSHOT, not UPDATE or APPEND.
        """
        if hasattr(self.client.datasets, "upload_dataframe"):
            try:
                self.client.datasets.upload_dataframe(
                    dataset_rid=dataset_rid,
                    dataframe=dataframe,
                    branch=self.branch_name,
                    transaction_type="SNAPSHOT",
                )
                return
            except PalantirRPCException as error:
                raise error

        self.__upload_dataframe_as_parquet_file(
            dataframe=dataframe,
            dataset_rid=dataset_rid,
        )

    def write_local_rows(
        self, file_path: str, columns: list[str], rows: list[dict]
    ) -> None:
        """Writes rows locally without calling Vantage."""
        csv_content = self.__rows_to_csv(columns=columns, rows=rows)
        self.__write_local_csv(file_path=file_path, csv_content=csv_content)

    def __upload_dataframe_as_parquet_file(
        self,
        dataframe: pd.DataFrame,
        dataset_rid: DatasetRid | str,
    ) -> None:
        table = pa.Table.from_pandas(dataframe, preserve_index=False)
        buffer = BytesIO()
        pq.write_table(table, buffer, compression="snappy")
        body = buffer.getvalue()

        try:
            self.client.datasets.Dataset.File.upload(
                dataset_rid=dataset_rid,
                file_path="data.parquet",
                body=body,
                branch_name=self.branch_name,
                transaction_type="SNAPSHOT",
            )
        except PalantirRPCException as error:
            raise error

    def __build_typed_dataframe(
        self, columns: list[str], rows: list[dict]
    ) -> pd.DataFrame:
        if columns == HEATHER_GITLAB_STATE_COLUMNS:
            return self.__build_dataframe_with_schema(
                columns=columns,
                rows=rows,
                integer_columns=STATE_INTEGER_COLUMNS,
                long_columns=STATE_LONG_COLUMNS,
                boolean_columns=STATE_BOOLEAN_COLUMNS,
            )

        if columns == HEATHER_GITLAB_COMMENTS_COLUMNS:
            return self.__build_dataframe_with_schema(
                columns=columns,
                rows=rows,
                integer_columns=COMMENT_INTEGER_COLUMNS,
                long_columns=COMMENT_LONG_COLUMNS,
                boolean_columns=COMMENT_BOOLEAN_COLUMNS,
            )

        return pd.DataFrame(data=rows, columns=columns)

    def __build_dataframe_with_schema(
        self,
        columns: list[str],
        rows: list[dict],
        integer_columns: list[str],
        long_columns: list[str],
        boolean_columns: list[str],
    ) -> pd.DataFrame:
        dataframe = pd.DataFrame(data=rows, columns=columns)

        for column in columns:
            if column in integer_columns:
                dataframe[column] = self.__to_nullable_integer_series(
                    dataframe=dataframe,
                    column=column,
                    dtype="Int32",
                )
            elif column in long_columns:
                dataframe[column] = self.__to_nullable_integer_series(
                    dataframe=dataframe,
                    column=column,
                    dtype="Int64",
                )
            elif column in boolean_columns:
                dataframe[column] = dataframe[column].map(self.__to_nullable_boolean)
                dataframe[column] = dataframe[column].astype("boolean")
            else:
                dataframe[column] = dataframe[column].where(
                    dataframe[column].notna(), None
                )
                dataframe[column] = dataframe[column].astype("object")

        return dataframe

    def __to_nullable_integer_series(
        self, dataframe: pd.DataFrame, column: str, dtype: str
    ) -> pd.Series:
        series = dataframe[column].replace("", pd.NA)
        series = pd.to_numeric(series, errors="coerce")
        return series.astype(dtype)

    def __to_nullable_boolean(self, value):
        if value is pd.NA or value is None:
            return pd.NA

        if isinstance(value, bool):
            return value

        value_text = str(value).strip().lower()

        if value_text in ["true", "1", "yes"]:
            return True

        if value_text in ["false", "0", "no"]:
            return False

        return pd.NA

    def __base_url(self) -> str:
        if self.hostname.startswith("https://") or self.hostname.startswith("http://"):
            return self.hostname.rstrip("/")

        return f"https://{self.hostname}".rstrip("/")

    def __build_foundry_client(self, verify: str | bool):
        if self.hostname == "" or self.token == "":
            return FoundryClient(config=Config(verify=verify))

        return FoundryClient(
            auth=UserTokenAuth(token=self.token),
            hostname=self.__sdk_hostname(),
            config=Config(verify=verify),
        )

    def __sdk_hostname(self) -> str:
        if self.hostname.startswith("https://"):
            return self.hostname.replace("https://", "", 1).rstrip("/")

        if self.hostname.startswith("http://"):
            return self.hostname.replace("http://", "", 1).rstrip("/")

        return self.hostname.rstrip("/")

    def __validate_remote_configuration(self) -> None:
        if self.hostname == "":
            raise RuntimeError("FOUNDRY_HOSTNAME or VANTAGE_HOSTNAME is required.")

        if self.token == "":
            raise RuntimeError("FOUNDRY_TOKEN or VANTAGE_TOKEN is required.")

    def __read_local_csv(self, file_path: str) -> list[dict]:
        with open(file=file_path, mode="r", encoding="UTF-8", newline="") as input_file:
            return list(DictReader(input_file))

    def __parse_csv(self, csv_content: str) -> list[dict]:
        csv_buffer = StringIO(csv_content)
        return list(DictReader(csv_buffer))

    def __rows_to_csv(self, columns: list[str], rows: list[dict]) -> str:
        csv_buffer = StringIO()
        writer = DictWriter(csv_buffer, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()

        for row in rows:
            writer.writerow({column: row.get(column, "") for column in columns})

        return csv_buffer.getvalue()

    def __write_local_csv(self, file_path: str, csv_content: str) -> None:
        output_directory_name = self.local_output_directory

        if output_directory_name == "":
            output_directory_name = ".data"

        output_directory = Path(output_directory_name)
        output_path = output_directory / file_path
        makedirs(name=output_directory, exist_ok=True)

        with open(
            file=output_path, mode="w", encoding="UTF-8", newline=""
        ) as output_file:
            output_file.write(csv_content)


def get_vantage_client() -> VantageClient:
    verify = getenv("FOUNDRY_VERIFY", False)

    if isinstance(verify, str) and verify.lower() in ["false", "0", "no"]:
        verify = False

    return VantageClient(verify=verify)
