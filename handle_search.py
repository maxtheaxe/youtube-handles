from glob import glob
from haralyzer import HarParser
from json import loads
import os
import pickle
import requests


def get_latest_har():
	all_files = glob(os.getcwd() + "/*")  # get list of files in own folder
	har_files = []
	for file in all_files:
		# if file is a youtube.com har file, save it
		if file.lower().endswith('.har') and ("youtube.com" in file.lower()):
			har_files.append(file)
	latest_har = max(har_files, key=os.path.getctime)
	return latest_har


def convert_headers(headers, want_cookies = True):
	# originally compressed, which postman and ff handled automatically
	# caused quite the headache figuring out why it couldn't be decoded
	unwanted_headers = ["Content-Length", "Accept-Encoding"]
	if not want_cookies:
		unwanted_headers.append("Cookie")
	new_headers = {}
	for kvp in headers:
		if kvp["name"] not in unwanted_headers:
			new_headers[kvp["name"]] = kvp["value"]
	return new_headers


def import_request(filename):
	# verify that it was a successful one(?)
	har_parser = HarParser.from_file(filename)
	# there should only be one request collected (for one page)
	target_request = har_parser.pages[0].post_requests[0]
	return target_request.url, convert_headers(target_request.request.headers), \
		loads(target_request.request["postData"]["text"])


def save_session(session):
	with open('cookies.pickle', 'wb') as f:
		pickle.dump(session.cookies, f)


def load_session():
	session = requests.session()  # or an existing session
	try:  # check if we've already saved updated cookies
		with open('cookies.pickle', 'rb') as f:
			session.cookies.update(pickle.load(f))
	except FileNotFoundError:  # otherwise, use those from HAR
		return session, False
	return session, True


def perform_request(session, url, headers, payload, username):
	payload["handle"] = username  # replace previous username with desired search term
	response = session.post(url, headers=headers, json=payload)
	response_data = loads(response.content.decode("latin-1"))
	save_session(session)
	# print(f"session cookies:\n{session.cookies}")
	if response_data["result"]["channelHandleValidationResultRenderer"]["result"]\
		== "CHANNEL_HANDLE_VALIDATION_RESULT_OK":
		return True, session
	return False, session


def main():
	latest_har = get_latest_har()
	session, session_existed = load_session()
	url, headers, payload = import_request(latest_har)
	new_usernames = ["mnawdhabwdaw7183", "hello", "silly", "stinky"]
	for username in new_usernames:
		success, session = perform_request(session, url, headers, payload, username)
		success_string = ""
		if not success:
			success_string = "not "
		# only print "not" if it fails
		# (tried to use ternary operator in fstring, but it looked gross)
		print(f"the handle '{username}' is {success_string}available")


if __name__ == "__main__":
	main()
