import requests

def create_session_with_cookies(cookies):
    """
    Creates a requests.Session and loads it with cookies obtained from Selenium.
    """
    session = requests.Session()
    
    # Load cookies into the session
    for cookie in cookies:
        session.cookies.set(cookie['name'], cookie['value'], domain=cookie['domain'])
    
    # Update headers to mimic a real browser
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
    })

    print("Requests 세션에 쿠키를 성공적으로 적용했습니다.")
    return session
