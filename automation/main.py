# Standard imports.
from os import getenv

# Local imports.
from scarab.spear.client import SpearClient
from scarab.vantage.client import VantageClient
from scarab.vantage.constants import (
    ACTIVITY_DATA_RID,
    AAR_DATA_RID,
    CONTACT_DATA_RID,
    TAG_DATA_RID,
    TICKET_DATA_RID,
    WEC_DATA_RID,
    TECH_EVAL_DATA_RID,
    TECH_EVAL_STATUS_UPDATE_DATA_RID,
    IMPLEMENTATION_DATA_RID,
    IMPLEMENTATION_STATUS_UPDATE_DATA_RID,
)

# Set the path to DOD certificates.
CURL_CA_BUNDLE = getenv(
    "CURL_CA_BUNDLE",
    "/usr/local/share/ca-certificates/Certificates_PKCS7_v5_14_DoD.der.crt",
)

# Define dataset and mediaset file names.
ticket_data_file_name = "ticket-data.csv"
tag_data_file_name = "tag-data.csv"
contact_data_file_name = "contact-data.csv"
wec_data_file_name = "wec-data.csv"
tech_eval_data_file_name = "tech-eval-data.csv"
tech_eval_status_update_data_file_name = "tech-eval-status-update-data.csv"
implement_data_file_name = "implementation-data.csv"
implement_status_update_data_file_name = "implementation-status-update-data.csv"
aar_data_file_name = "aar-data.csv"
activity_data_file_name = "activity-data.csv"

# Init a SPEAR client.
spear = SpearClient(verify=CURL_CA_BUNDLE)
vantage = VantageClient(verify=CURL_CA_BUNDLE)

print("[*] Extracting ticket data")
ticket_data = spear.get_ticket_data()
print(
    f"[*] ticket-data columns ({len(ticket_data.columns)}): {list(ticket_data.columns)}"
)

print("[*] Loading ticket data into Vantage")
vantage.upload_dataframe_as_csv(
    dataframe=ticket_data,
    dataset_rid=TICKET_DATA_RID,
    filename_to_use_in_vantage=ticket_data_file_name,
)

print("[*] Extracting tag data")
tag_data = spear.get_tag_data(ticket_ids=ticket_data["Ticket ID"])
print(f"[*] tag-data columns ({len(tag_data.columns)}): {list(tag_data.columns)}")

print("[*] Loading tag data into Vantage")
vantage.upload_dataframe_as_csv(
    dataframe=tag_data,
    dataset_rid=TAG_DATA_RID,
    filename_to_use_in_vantage=tag_data_file_name,
)

print("[*] Extracting contact data")
contact_data = spear.get_contact_data(ticket_ids=ticket_data["Ticket ID"])
print(
    f"[*] contact-data columns ({len(contact_data.columns)}): {list(contact_data.columns)}"
)

print("[*] Loading contact data into Vantage")
vantage.upload_dataframe_as_csv(
    dataframe=contact_data,
    dataset_rid=CONTACT_DATA_RID,
    filename_to_use_in_vantage=contact_data_file_name,
)

print("[*] Extracting WEC data")
wec_data = spear.get_wec_data(ticket_ids=ticket_data["Ticket ID"])
print(f"[*] wec-data columns ({len(wec_data.columns)}): {list(wec_data.columns)}")

print("[*] Loading WEC data into Vantage")
vantage.upload_dataframe_as_csv(
    dataframe=wec_data,
    dataset_rid=WEC_DATA_RID,
    filename_to_use_in_vantage=wec_data_file_name,
)

print("[*] Extracting technical evaluation data")
tech_eval_data = spear.get_tech_eval_data(ticket_ids=ticket_data["Ticket ID"])
print(
    f"[*] tech-eval-data columns ({len(tech_eval_data.columns)}): {list(tech_eval_data.columns)}"
)

print("[*] Loading technical evaluation data into Vantage")
vantage.upload_dataframe_as_csv(
    dataframe=tech_eval_data,
    dataset_rid=TECH_EVAL_DATA_RID,
    filename_to_use_in_vantage=tech_eval_data_file_name,
)

print("[*] Extracting technical evaluation status updates")
tech_eval_status_update_data = spear.get_tech_eval_status_updates(
    ticket_ids=ticket_data["Ticket ID"]
)
print(
    f"[*] tech-eval-status-update-data columns ({len(tech_eval_status_update_data.columns)}): {list(tech_eval_status_update_data.columns)}"
)

print("[*] Loading technical evaluation status updates into Vantage")
vantage.upload_dataframe_as_csv(
    dataframe=tech_eval_status_update_data,
    dataset_rid=TECH_EVAL_STATUS_UPDATE_DATA_RID,
    filename_to_use_in_vantage=tech_eval_status_update_data_file_name,
)

print("[*] Extracting implementation data")
implement_data = spear.get_implementation_data(ticket_ids=ticket_data["Ticket ID"])
print(
    f"[*] implementation-data columns ({len(implement_data.columns)}): {list(implement_data.columns)}"
)

print("[*] Loading implementation data into Vantage")
vantage.upload_dataframe_as_csv(
    dataframe=implement_data,
    dataset_rid=IMPLEMENTATION_DATA_RID,
    filename_to_use_in_vantage=implement_data_file_name,
)

print("[*] Extracting implementation status updates")
implement_status_update_data = spear.get_implementation_status_updates(
    ticket_ids=ticket_data["Ticket ID"]
)
print(
    f"[*] implementation-status-update-data columns ({len(implement_status_update_data.columns)}): {list(implement_status_update_data.columns)}"
)

print("[*] Loading implementation status updates into Vantage")
vantage.upload_dataframe_as_csv(
    dataframe=implement_status_update_data,
    dataset_rid=IMPLEMENTATION_STATUS_UPDATE_DATA_RID,
    filename_to_use_in_vantage=implement_status_update_data_file_name,
)

print("[*] Extracting AAR data")
aar_data = spear.get_aar_data(ticket_ids=ticket_data["Ticket ID"])
print(f"[*] aar-data columns ({len(aar_data.columns)}): {list(aar_data.columns)}")

print("[*] Loading AAR data into Vantage")
vantage.upload_dataframe_as_csv(
    dataframe=aar_data,
    dataset_rid=AAR_DATA_RID,
    filename_to_use_in_vantage=aar_data_file_name,
)

print("[*] Extracting activity data")
activity_data = spear.get_activity_data(ticket_ids=ticket_data["Ticket ID"])
print(
    f"[*] activity-data columns ({len(activity_data.columns)}): {list(activity_data.columns)}"
)

print("[*] Loading activity data into Vantage")
vantage.upload_dataframe_as_csv(
    dataframe=activity_data,
    dataset_rid=ACTIVITY_DATA_RID,
    filename_to_use_in_vantage=activity_data_file_name,
)

