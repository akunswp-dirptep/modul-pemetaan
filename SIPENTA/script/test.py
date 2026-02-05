import arcpy, os, sys, requests, json

#========== Proses Login ==========
arcpy.AddMessage('========== Proses Login ==========')
username = arcpy.GetParameterAsText(0)
password = arcpy.GetParameterAsText(1)

if username and password:
##    url = "http://webgis.co.id:10280/api/index.php/api_sipenta/login"
    url = "https://sipenta.atrbpn.go.id/api/index.php/api_sipenta/login"

    session = requests.Session()
    response = session.get(url)
    client = requests.session()
    client.get(url)
    if 'tokencsrf' in client.cookies:
        csrftoken = client.cookies['tokencsrf']
    else:
        csrftoken = client.cookies['tokencsrf']

    cookies = {'tokencsrf': csrftoken}
    data = {"username": username, "password": password, 'tokencsrf': csrftoken}

    r = requests.post(url, cookies=cookies, data=data).text
    arcpy.AddMessage(r)

##    data = {"username": username, "password": password}
##    x = requests.post(url, data).text
##    arcpy.AddMessage(x)

##    try:
##        response = urllib.request.urlopen(url)
##        if response.getcode() == 200:
##            arcpy.AddMessage('Bingo')
##            data = (response.getheader('Set-Cookie')).split(";")[0]
##            csrf_name = data.split("=")[0]
##            csrf_code = data.split("=")[1]
##            arcpy.AddMessage(csrf_name)
##            arcpy.AddMessage(csrf_code)
##
##            cookies = {csrf_name: csrf_code}
##            data = {"username": username, "password": password, csrf_name:csrf_code}
##            x = requests.post(url, data=data, cookies=cookies).text
##            arcpy.AddMessage(x)
##        else:
##            arcpy.AddMessage('The response code was not 200, but: {}'.format(response.get_code()))
##    except urllib.error.HTTPError as e:
##        arcpy.AddMessage('''An error occurred: {} The response code was {}'''.format(e, e.getcode()))
##

##    cookiejar = http.cookiejar.CookieJar()
##    cookieproc = urllib.request.HTTPCookieProcessor(cookiejar)
##    opener = urllib.request.build_opener(cookieproc)
##    response = opener.open(url)
##    for cookie in cookiejar:
##        arcpy.AddMessage(cookie.name)
##        arcpy.AddMessage(cookie.value)
##
##        data = {"username": username, "password": password, cookie.name: cookie.value}
##        x = requests.post(url, json=data).text
##        arcpy.AddMessage(x)

    
##
##    login_data = dict(username=username, password=password, csrfmiddlewaretoken=csrftoken, next='/')
####    x = client.post(url, data=login_data, headers=dict(Referer=url))
####    data = {"username": username, "password": password, 'aliasscsrf': csrftoken}
####    x = requests.post(url, data).text

##    x = requests.post(url, data=login_data).text
    
##        if x == 'username dan password salah, login gagal !':
##            arcpy.AddMessage('Gagal Login')
##        else :
##    ##        y = json.loads(x)
##            arcpy.AddMessage(x)
