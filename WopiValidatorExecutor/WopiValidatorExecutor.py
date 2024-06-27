import json
import logging
import requests
import sys
from colorama import init, Fore
from xml.etree import ElementTree

from .constants import *

def get_indented_json_dump(input_json):
    return json.dumps(input_json, sort_keys=True, indent=4, separators=(',', ': '))

def get_wopi_test_endpoint(wopi_discovery_service_url):
    logging.info("WOPI Discovery Service Url: " + wopi_discovery_service_url)
    try:
        discovery_service_response = requests.get(wopi_discovery_service_url)
        discovery_service_response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(Fore.RED + f"Failed to retrieve WOPI Discovery Service XML: {str(e)}")
        logging.critical("Failed to retrieve WOPI Discovery Service XML", exc_info=True)
        sys.exit(1)

    try:
        discovery_xml = ElementTree.fromstring(discovery_service_response.content)
        wopi_test_endpoint_url = discovery_xml.find(WOPITESTAPPLICATION_NODE_PATH).attrib[WOPITESTAPPLICATION_URLSRC_ATTRIBUTE]
    except Exception as e:
        print(Fore.RED + f"Failed to parse WOPI Discovery Service XML: {str(e)}")
        logging.critical("Failed to parse WOPI Discovery Service XML", exc_info=True)
        sys.exit(1)

    return wopi_test_endpoint_url[:wopi_test_endpoint_url.find('?')]

def execute_wopi_validator(wopi_discovery_service_url, payload):
    # Initialize colorama to allow applying colors to the output text.
    init(autoreset=True)

    wopi_test_endpoint = get_wopi_test_endpoint(wopi_discovery_service_url)
    logging.info("WopiValidator TestEndpoint Url: " + wopi_test_endpoint)

    print(Fore.CYAN + "..........................WopiValidator Execution Starts....................................\n")

    # Get the TestUrls by calling WopiValidator Endpoint.
    try:
        test_url_response = requests.get(wopi_test_endpoint, params=payload)
        test_url_response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(Fore.RED + f"Failed to retrieve TestUrls: {str(e)}")
        logging.critical("Failed to retrieve TestUrls", exc_info=True)
        sys.exit(1)

    testurls = test_url_response.json()
    logging.info("TestUrls to be Executed : \n" + get_indented_json_dump(testurls))

    # Execute tests.
    for testurl in testurls:
        try:
            test_result_response = requests.get(testurl)
            test_result_response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(Fore.RED + f"Execution Failed for TestUrl {testurl}: {str(e)}")
            logging.error(f"Execution Failed for TestUrl {testurl}", exc_info=True)
            continue

        # Log the json response for the test being executed.
        test_result = test_result_response.json()
        logging.info("Result for TestUrl:" + testurl + '\n')
        logging.info(get_indented_json_dump(test_result))

        # Print the test result and failure reasons if any.
        test_case = test_result.get(TEST_NAME)
        error_msg = test_result.get(TEST_ERROR_MSG)
        msg_color = Fore.GREEN
        if error_msg:
            if error_msg == TEST_ERROR_SKIPPED:
                msg_color = Fore.YELLOW
                print(test_case + msg_color + "...Skipped...\n")
            else:
                msg_color = Fore.RED
                print(test_case + msg_color + "...Failed...\n")
            print(msg_color + error_msg + '\n')
            request_details = test_result.get(REQUEST_DETAILS, [])
            for requestDetail in request_details:
                validation_failures = requestDetail.get(REQUEST_VALIDATION_FAILURE, [])
                failed_request_name = requestDetail.get(REQUEST_NAME, "")
                if validation_failures:
                    print(msg_color + "Request Failed: " + failed_request_name)
                    print(msg_color + "*****************FailureReason Starts*********************")
                    for validationFailure in validation_failures:
                        print(msg_color + validationFailure)
                    print(msg_color + "*****************FailureReason Ends***********************\n")
        else:
            print(test_case + msg_color + "...Passed...\n")

    print(Fore.CYAN + "..........................WopiValidator Execution Ends....................................")

