import csv
from glob import glob
from haralyzer import HarParser
from json import loads
import os
import pickle
from random import randint
import requests
import time


def get_latest_har(log):
	all_files = glob(os.getcwd() + "/*")  # get list of files in own folder
	har_files = []
	for file in all_files:
		# if file is a youtube.com har file, save it
		if file.lower().endswith('.har') and ("youtube.com" in file.lower()):
			har_files.append(file)
	latest_har = max(har_files, key=os.path.getctime)
	if log:
		print(f"using latest HAR file: {latest_har}")
	return latest_har


def import_usernames(filename, log):
	usernames = []
	num_names = 0
	with open(filename) as csv_file:
		for row in csv_file:
			if len(row[:-1]) >= 3:  # don't import usernames less than three chars
				usernames.append(row[:-1])
	if log:
		print(f"successfully imported {num_names} usernames from {filename}")
	return usernames


def save_results(results, log):
	with open("results.csv", "w", encoding="UTF8", newline="") as f:
		writer = csv.writer(f)
		writer.writerow(("username", "available"))
		writer.writerows(results)
	if log:
		print(f"successfully saved {len(results)} results")


def convert_headers(headers, want_cookies):
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


def import_request(filename, want_cookies):
	# verify that it was a successful one(?)
	har_parser = HarParser.from_file(filename)
	# there should only be one request collected (for one page)
	target_request = har_parser.pages[0].post_requests[0]
	return target_request.url, \
		   convert_headers(target_request.request.headers, want_cookies), \
		   loads(target_request.request["postData"]["text"])


def load_session(log=False):
	session = requests.session()  # or an existing session
	try:  # check if we've already saved updated cookies
		with open("cookies.pickle", "rb") as f:
			session.cookies.update(pickle.load(f))
	except FileNotFoundError:  # otherwise, use those from HAR
		return session, False
	if log:
		print("using existing cookies from previous usage")
	return session, True


def save_session(session, log):
	with open("cookies.pickle", "wb") as f:
		pickle.dump(session.cookies, f)
	if log:
		print("cookies successfully saved")


def delete_session(log):
	os.remove("cookies.pickle")
	if log:
		print("cookies successfully removed")


def check_username(session, url, headers, payload, username, log):
	payload["handle"] = username  # replace previous username with desired search term
	response = session.post(url, headers=headers, json=payload)
	response_data = loads(response.content)
	# print("response data:\n", response_data)
	save_session(session, log)
	# print(f"session cookies:\n{session.cookies}")
	status = response.status_code  # for passing additional info to main loop of program
	try:
		if response_data["result"]["channelHandleValidationResultRenderer"]["result"] \
				== "CHANNEL_HANDLE_VALIDATION_RESULT_OK":
			return True, session, status
	except KeyError as err:
		if response.status_code == 401:
			print("logged out—saving and shutting down")
		elif response.status_code == 429:
			print("rate limit! sleeping...")
		else:
			print(f"unknown error #{status}, save this message: {response.content}")
	return False, session, status


def run_full_search(usernames, log):
	latest_har = get_latest_har(log)
	session, session_existed = load_session()
	# if session already existed, we don't collect cookies from HAR
	url, headers, payload = import_request(latest_har, (not session_existed))
	results = []
	rate_limit_counter = 0
	for username in usernames:
		random_element = randint(0, 9)  # add randomness to sleep time
		time.sleep(random_element)
		success, session, status = check_username(session, url, headers, payload, username, log)
		results.append((username, success))
		if log:
			success_string = ""
			if not success:
				success_string = "not "
			# only print "not" if it fails
			# (tried to use ternary operator in fstring, but it looked gross)
			print(f"the handle '{username}' is {success_string}available")
		if status == 200:
			continue  # business as usual
		elif status == 429:  # rate limit, slowing down
			rate_limit_counter += 1
			# if already limit 10 times (even with delays), exit
			if rate_limit_counter >= 10:
				return results, status
			# sleep for progressively more time (with random element)
			time.sleep((rate_limit_counter + 1) * (60 + random_element))
		else:  # something went wrong, exit gracefully
			return results, status
	return results, 200


def main():
	log = True  # set to true if you want to print program logs
	# usernames = ["smelly", "tiola1396u", "lolman"]
	usernames = import_usernames("usernames.csv", log)
	results, status = run_full_search(usernames, log)
	save_results(results, log)  # log what we have, regardless of whether completed
	if status != 200:  # if something went wrong, search exited early
		if status == 401:  # logged out condition
			delete_session(log)  # old cookies are stale, we'll get new ones from HAR
			raise Exception("time to download a new HAR file!" + \
							" (youtube logged you out, be careful)")
		elif status == 429:  # rate limit condition
			raise Exception("you've been rate limited 10 times already!" + \
							" if I were you, I'd take the rest of the day off")
		else:  # unknown error condition
			raise Exception("unknown error occurred—youtube must've changed their API" + \
							" (please tell me!)")


if __name__ == "__main__":
	main()
