from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import WebDriverException, UnexpectedAlertPresentException
from bs4 import BeautifulSoup
import time
import datetime
import sys, os, getopt
import csv


# Get local session of firefox
g_browser = webdriver.Firefox()
g_keyword_arg = ""
g_log_file = "log.txt"
g_max_log_lines = 10000
g_idx_for_log = 0
g_output_csv_folder = "csv_output"
g_log_folder = "log"
g_csv_filename = "email_address.csv"
g_linked_email = "henrirehn1984@gmail.com"
g_linked_pwd = "luckyhenrisocial"
g_profile_links = []


def print_to_log(str_to_log):
    # Write a log file
    print(str_to_log)
    global g_log_file, g_max_log_lines, g_idx_for_log
    ts = time.time()
    st = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')

    g_idx_for_log += 1
    fo = open(g_log_file, "a")
    try:
        # str_to_log += "----------log line cnt: %s" % g_idx_for_log
        str_to_log = str_to_log.encode("utf8", "ignore")
        fo.write(st + "\t: " + str_to_log + "\n")
    except:
        pass
    fo.close()
    if g_idx_for_log >= g_max_log_lines:
        open(g_log_file, 'w').close()
        g_idx_for_log = 0


def linked_in_login():
    # login
    global g_linked_email, g_linked_pwd
    global g_browser

    g_browser.get("https://www.linkedin.com/")
    strtmp = "document.getElementById('session_key-login').value = '%s';" % g_linked_email
    strtmp += "document.getElementById('session_password-login').value = '%s';" % g_linked_pwd
    try:
        g_browser.execute_script(strtmp)
        element = g_browser.find_elements_by_xpath("//input[@id='signin']")[0]
        element.click()
        print_to_log("linkedin logged in successfully!!!")
        return 0
    except WebDriverException:
        print_to_log("linkedin log in failed!!!")
        return -1
    return 0


def go_to_search_page():
    global g_browser, g_keyword_arg, g_profile_links
    element = g_browser.find_elements_by_xpath("//select[@id='main-search-category']/option[@class='people']")[0]
    element.click()

    strtmp = "document.getElementById('main-search-box').value = '%s';" % g_keyword_arg
    g_browser.execute_script(strtmp)

    element = g_browser.find_elements_by_xpath("//button[@class='search-button']")[0]
    element.click()

    time.sleep(3)

    next_btn = g_browser.find_elements_by_xpath("//ul[@class='pagination']/li[@class='next']/a[@class='page-link']")

    while len(next_btn) > 0:
        element = g_browser.find_elements_by_xpath("//ol[@class='search-results']//li[contains(@class,'people')]")
        for each in element:
            g_profile_links.append(each.find_elements_by_xpath("./a")[0].get_attribute('href'))
        next_btn[0].click()
        time.sleep(3)
        next_btn = g_browser.find_elements_by_xpath("//ul[@class='pagination']//"
                                                    "li[@class='next']/a[@class='page-link']")

    element = g_browser.find_elements_by_xpath("//ol[@class='search-results']//li[contains(@class,'people')]")
    if element:
        for each in element:
            g_profile_links.append(each.find_elements_by_xpath("./a")[0].get_attribute('href'))


def get_email_addresses():
    global g_browser, g_profile_links
    f = open(g_csv_filename, 'wb')
    w = csv.writer(f, dialect='excel')
    for each_link in g_profile_links:
        print each_link
        g_browser.get(each_link)
        delay = 10
        try:
            element = WebDriverWait(g_browser, delay)\
                .until(EC.presence_of_element_located((By.ID, "footer")))
            page_html = g_browser.page_source
            t_soup = BeautifulSoup(page_html, 'html5lib')
            t_div = t_soup.find("div", {"id": "email-view"})
            if t_div:
                for link in t_div.findAll('a'):
                    w.writerow([link.text, ])
        except TimeoutException:
            pass
        except WebDriverException:
            pass
        except UnexpectedAlertPresentException:
            pass
    f.close()


def main():
    global g_keyword_arg
    linked_in_login()
    go_to_search_page()
    get_email_addresses()

if __name__ == "__main__":
    g_profile_links = []
    arg_v = sys.argv[1:]
    try:
        opts, args = getopt.getopt(arg_v, "k:", ["keyword="])
    except getopt.GetoptError:
        sys.exit(2)
    for opt, arg in opts:
        if opt in ("-k", "--keyword"):
            g_keyword_arg = arg

    print_to_log('Keyword is %s' % g_keyword_arg)

    if not os.path.exists(g_output_csv_folder):
        os.makedirs(g_output_csv_folder)
    if not os.path.exists(g_log_folder):
        os.makedirs(g_log_folder)

    g_csv_filename = "%s/email_addresses_for_%s.csv" % (g_output_csv_folder, g_keyword_arg)
    g_log_file = "%s/log_%s.txt" % (g_log_folder, g_keyword_arg)

    # Is Being Run Directly
    main()