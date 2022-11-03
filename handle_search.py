from haralyzer import HarParser
from json import loads, dumps
import pickle
import requests


def convert_headers(headers):
	unwanted_headers = ["Content-Length", "Accept-Encoding"]
	new_headers = {}
	for kvp in headers:
		if kvp["name"] not in unwanted_headers:
			new_headers[kvp["name"]] = kvp["value"]
		# else:
		# 	new_headers["Content-Length"]
	return new_headers


def import_request(filename):
	# verify that it was a successful one(?)
	har_parser = HarParser.from_file(filename)
	# there should only be one request collected (for one page)
	target_request = har_parser.pages[0].post_requests[0]
	# print("url:\n", target_request.request.url)
	# print("headers:\n", convert_headers(target_request.request.headers))
	# print("payload:\n", loads(target_request.request["postData"]["text"]))
	return target_request.url, convert_headers(target_request.request.headers), \
		loads(target_request.request["postData"]["text"])


def load_session():
	session = requests.session()  # or an existing session
	try:  # check if we've already saved updated cookies
		with open('cookies.pickle', 'rb') as f:
			session.cookies.update(pickle.load(f))
	except FileNotFoundError:  # otherwise, use those from HAR
		return session, False
	return session, True


def conduct_request(session, url, headers, payload, username):
	payload["handle"] = username  # replace previous username with desired search term
	response = requests.post(url, headers=headers, json=payload)
	# print("request url:\n", response.request.url)
	# print("request headers:\n", response.request.headers)
	# print("request data:\n", response.request.body)
	# print("response headers:\n", response.headers)
	# print("response status:\n", response.status_code)
	# print("response encoding:\n", response.encoding)
	# print("raw response:\n", response.content)
	# from charset_normalizer import detect, normalize
	# print(f"actual char type: {detect(response.content)}")
	response_data = loads(response.content.decode("latin-1"))
	if response_data["result"]["channelHandleValidationResultRenderer"]["result"]\
		== "CHANNEL_HANDLE_VALIDATION_RESULT_OK":
		return True
	return False



def pretty_print_POST(req):
	"""
	At this point it is completely built and ready
	to be fired; it is "prepared".

	However pay attention at the formatting used in
	this function because it is programmed to be pretty
	printed and may differ from the actual request.
	"""
	# pretty_print_POST(requests.Request('POST', url, headers=headers, data = payload).prepare())
	print('{}\n{}\r\n{}\r\n\r\n{}'.format(
		'-----------START-----------',
		req.method + ' ' + req.url,
		'\r\n'.join('{}: {}'.format(k, v) for k, v in req.headers.items()),
		req.body,
	))


def main():
	session, session_existed = load_session()
	new_username = "mnawdhabwdaw7183"
	url, headers, payload = import_request("www.youtube.com_Archive [22-11-03 21-53-57].har")
	success = conduct_request(session, url, headers, payload, new_username)
	success_string = ""
	if not success:
		success_string = "not "
	# only print "not" if it fails
	# (tried to use ternary operator in fstring, but it looked gross)
	print(f"the handle '{new_username}' is {success_string}available")


if __name__ == "__main__":
	main()
