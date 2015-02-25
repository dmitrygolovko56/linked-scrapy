from selenium import webdriver
from selenium import selenium
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import WebDriverException
from selenium.common.exceptions import NoSuchElementException
from bs4 import BeautifulSoup
import time
import datetime
import sys, os, getopt
import pytz
import re
from dateutil import parser

g_browser = webdriver.Firefox() # Get local session of firefox
g_fb_email = ""
g_fb_pwd = ""

g_status_folder = "status"
g_output_xmls_folder = "output_xmls"
g_log_folder = "log"
g_xmlfilename = "FBComments_result.xml"
g_statusfilename = "status.txt"
g_statusCompanyfilename = "status_company.txt"
g_log_file = "log.txt"
g_max_log_lines = 10000
g_idx_for_log = 0
g_interval = 1
g_seeds = []

g_old_com_name = ""
g_old_year_no = 0
g_old_post_no = 0
g_old_item_no = 0
g_isfilevalid = False
g_date_arg = ""
g_stock_arg = ""
g_companyURL_arg = ""

g_processed_com_lst = []


def print_to_log(str_to_log):
    #write a log file
    print(str_to_log)
    global g_log_file, g_max_log_lines, g_idx_for_log
    ts = time.time()
    st = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')

    g_idx_for_log += 1
    fo = open(g_log_file, "a")
    try:
        #str_to_log += "----------log line cnt: %s" % g_idx_for_log
        str_to_log = str_to_log.encode("utf8", "ignore")
        fo.write( st + "\t: " + str_to_log + "\n" )
    except:
        pass
    fo.close()
    if g_idx_for_log >= g_max_log_lines:
        open(g_log_file, 'w').close()
        g_idx_for_log = 0


def CDATA(text=None):
    text = "<![CDATA[%s]]>" % text
    return text


def focus_on_window():
    global g_browser, g_interval
    g_browser.select_window("null") #select the main window
    time.sleep(1*g_interval)


def process_one_page(year_idx, post_idx, one_com, one_url):
    global g_browser, g_interval
    global g_seeds, g_xmlfilename, g_statusfilename
    global g_old_com_no, g_old_year_no, g_old_post_no, g_old_item_no
    global g_date_arg

    #print_to_log("processing >>> %s" % (one_url))
    g_browser.get(one_url)
    time.sleep(g_interval*10)
    #focus_on_window()
    #expand all "View more comments"
    #ShowComments_elements = g_browser.find_elements_by_xpath("//a[@class='UFIBlingBoxTimelineItem']")
    #ShowComments_elements = g_browser.find_elements_by_xpath("//a[@aria-label='Show comments']")
    while True:
        try:
            ViewMoreComments = g_browser.find_element_by_link_text("View more comments")
            ViewMoreComments.click()
            time.sleep(g_interval*2)
        except NoSuchElementException:
            break
        except:
            break

    while True:
        try:
            ViewMoreComments = g_browser.find_elements_by_xpath("//a[@class='UFIPagerLink']")
            ViewMoreComments.click()
            time.sleep(g_interval*2)
        except NoSuchElementException:
            break
        except:
            break

    loop_flag = True
    item_idx = 0
    while loop_flag:
        #Company, Page URL, Date/Time Crawled, (Comment or Share),
        #if comment then continue as //  Author Name, Text Comment, Date/Time of Comment, (Mobile or No), Number of Likes obtained by Comment,
        #Name of Company Post under which the Comment is Nested.
        t_Company = one_url.split("/")[-1]
        t_Stock = one_com
        t_PageURL = one_url
        t_AuthorName = ""
        t_TextComment = ""
        t_CommentDate = ""
        t_Mobile = ""
        t_NumberOfLikes = ""

        page_html = g_browser.page_source
        t_soup = BeautifulSoup(page_html,'html5lib')
        t_lis = t_soup.findAll('li',attrs={'class':['UFIRow','UFIComment','UFIComponent']})
        for t_li in t_lis:
            if g_old_com_name == one_com and year_idx == g_old_year_no and post_idx == g_old_post_no and item_idx < g_old_item_no:
                #already done
                pass
            else:
                t_CommentDate_to_compare = ""
                try:
                    #t_CommentDate
                    t_abbrs = t_li.findAll('abbr', attrs={'class':['livetimestamp']})
                    #pstr = ''.join(t_abbrs[0].findAll(text=True) ).replace('\r\n', ' ')
                    pstr = t_abbrs[0].get("title")
                    dt = parser.parse(pstr.strip())
                    t_CommentDate = dt.strftime('%Y-%m-%d %H:%M:%S %Z')
                    #20140416
                    t_CommentDate_to_compare = dt.strftime('%Y%m%d')
                except:
                    pass

                if len(g_date_arg) > 0 and (t_CommentDate_to_compare == "" or t_CommentDate_to_compare < g_date_arg):
                    item_idx += 1
                    continue

                #write to status file
                fo = open(g_statusfilename, "wb")
                strtemp = "year_no=%s,post_no=%s,item_no=%s,com_name=%s" % (year_idx, post_idx, item_idx, one_com)
                fo.write( strtemp)
                fo.close()

                try:
                    t_as = t_li.findAll('a', attrs={'class':['UFICommentActorName']})
                    #t_AuthorName
                    pstr = ''.join(t_as[0].findAll(text=True) ).replace('\r\n', ' ')
                    t_AuthorName = pstr.strip()
                except:
                    pass

                try:
                    #t_TextComment
                    t_spans = t_li.findAll('span', attrs={'class':['UFICommentBody']})
                    pstr = ''.join(t_spans[0].findAll(text=True) ).replace('\r\n', ' ')
                    t_TextComment = pstr.strip()
                except:
                    pass

                #t_Mobile

                try:
                    #t_NumberOfLikes
                    t_as = t_li.findAll('a', attrs={'class':['UFICommentLikeButton']})
                    pstr = ''.join(t_as[0].findAll(text=True) ).replace('\r\n', ' ')
                    t_NumberOfLikes = pstr.strip()
                except:
                    pass

                #TimeStamp
                timestamp = time.time()
                utc = datetime.datetime.utcfromtimestamp(timestamp)
                utc = pytz.utc.localize(utc)
                # Format string
                format = "%Y-%m-%d %H:%M:%S %Z"
                # Print UTC time
                t_TimeStamp = utc.strftime(format)
                try:
                    #write to file
                    fo = open(g_xmlfilename, "r+")
                    pos = len("</data>") * (-1)
                    fo.seek(pos, 2)

                    t_str2 = '<Company>%s</Company>' % CDATA(t_Company)
                    t_str = t_str2
                    t_str2 = '<PageURL>%s</PageURL>' % CDATA(t_PageURL)
                    t_str += t_str2
                    t_str2 = '<Stock>%s</Stock>' % CDATA(t_Stock)
                    t_str += t_str2
                    t_str2 = '<AuthorName>%s</AuthorName>' % CDATA(t_AuthorName)
                    t_str += t_str2
                    t_str2 = '<TextComment>%s</TextComment>' % CDATA(t_TextComment)
                    t_str += t_str2
                    t_str2 = '<CommentDate>%s</CommentDate>' % CDATA(t_CommentDate)
                    t_str += t_str2
                    t_str2 = '<Mobile>%s</Mobile>' % CDATA(t_Mobile)
                    t_str += t_str2
                    t_str2 = '<NumberOfLikes>%s</NumberOfLikes>' % t_NumberOfLikes
                    t_str += t_str2
                    t_str2 = '<Crawled_TimeStamp>%s</Crawled_TimeStamp>' % t_TimeStamp
                    t_str += t_str2

                    t_comment = '<Comment>%s</Comment></data>' % t_str
                    fo.write( t_comment )
                    fo.close()
                except:
                    pass
            item_idx += 1
        #View previous comments
        try:
            ViewPrevComments = g_browser.find_element_by_link_text("View previous comments")
            ViewPrevComments.click()
            time.sleep(g_interval*2)
        except NoSuchElementException:
            break
        except:
            break

    return

def fb_login():
    #login
    global g_fb_email, g_fb_pwd
    global g_browser

    g_browser.get("https://www.facebook.com/")
    strtmp = "document.getElementById('email').value = '%s';" % (g_fb_email)
    strtmp += "document.getElementById('pass').value = '%s';" % (g_fb_pwd)
    try:
        g_browser.execute_script(strtmp)
        lbl_elements = g_browser.find_elements_by_xpath("//label[@id='loginbutton']")
        element=lbl_elements[0].find_element_by_xpath("//input[@type='submit']")
        element.click()
        time.sleep(10)
        print_to_log("facebook logged in successfully!!!")
        return 0
    except WebDriverException:
        print_to_log("facebook log in failed!!!")
        return -1
    return 0

def process_one_company(one_com, com_url):
    global g_browser, g_interval
    global g_seeds, g_xmlfilename, g_statusfilename
    global g_old_com_name, g_old_year_no, g_old_post_no, g_old_item_no

    print_to_log("processing >>> Stock: %s, %s" % (one_com, com_url))
    g_browser.get(com_url)
    time.sleep(g_interval * 10)
    page_html=g_browser.page_source
    #get Year links
    try:
        t_soup = BeautifulSoup(page_html,'html5lib')
        t_uls = t_soup.findAll('ul',attrs={'class':['fbTimelineScrubber', 'fixed_elem']})
        t_lis = t_uls[0].findAll('li', attrs={'class': 'clearfix'})
    except:
        print_to_log("Can't crawl company: %s, %s" % (one_com, com_url))
        return

    year_idx = 0
    for t_li in t_lis:
        #print t_li['data-key']
        is_valid_li = False
        try:
            if t_li['data-year'] in t_li['data-key']:
                is_valid_li = True
        except:
            pass
        if is_valid_li:
            #year link
            t_as = t_li.findAll('a')
            for t_a in t_as:
                pstr = ''.join(t_a.findAll(text=True) ).replace('\r\n', ' ')
                pstr = pstr.strip()
                if t_li['data-year'] in pstr:
                    #got year link
                    one_url = "%s/timeline/%s" % (com_url, t_li['data-year'])

                    if g_old_com_name == one_com and year_idx < g_old_year_no:
                        #already processed
                        pass
                    else:
                        #print(one_url)
                        print_to_log("processing >>> Year: %s, %s" % (t_li['data-year'], one_url))
                        ###get posts now
                        g_browser.get(one_url)
                        time.sleep(g_interval * 10)
                        page_html2 = g_browser.page_source
                        t_soup2 = BeautifulSoup(page_html2, 'html5lib')
                        t_as2 = t_soup2.findAll('a', attrs={'class': ['uiLinkSubtle']})
                        post_idx = 0
                        for t_a2 in t_as2:
                            if g_old_com_name == one_com and year_idx == g_old_year_no and post_idx < g_old_post_no:
                                #already done
                                pass
                            else:
                                #try:
                                post_url = t_a2.get('href')
                                #https://www.facebook.com
                                if not post_url.startswith("http"):
                                    post_url = "https://www.facebook.com%s" % post_url
                                if not post_url.endswith(".com#"):
                                    print_to_log("processing >>> Post: %s, %s" % (post_idx, post_url))
                                    process_one_page(year_idx, post_idx, one_com, post_url)
                                #except:
                                #    pass
                            post_idx += 1

                    year_idx += 1

    return


def readConfiguration():
    conf = {}
    conf["KO"] = "https://www.facebook.com/cocacola"
    conf["MSFT"] = "https://www.facebook.com/Microsoft"
    return conf


def main():
    global g_seeds, g_xmlfilename, g_statusfilename, g_statusCompanyfilename
    global g_old_com_name, g_old_year_no, g_old_post_no, g_old_item_no
    global g_isfilevalid
    global g_processed_com_lst

    try:
        ins = open( g_statusCompanyfilename, "r" )
        for line in ins:
            if len(line.strip()) > 0:
                g_processed_com_lst.append(line.strip())
    except IOError:
        pass
    except:
        pass

    ### read facebook account
    #facebook_email:grytsenko.bamboo@gmail.com
    #facebook_password:panda123bamboo.
    fb_filename = "fb_account.txt"
    try:
        ins = open( fb_filename, "r" )
        for line in ins:
            p = re.compile(r'^facebook_email:(?P<param>.*)$')
            m = p.search( line.rstrip() )
            if m is not None and m.group('param') is not None:
                g_fb_email = m.group('param')

            p = re.compile(r'^facebook_password:(?P<param>.*)$')
            m = p.search( line.rstrip() )
            if m is not None and m.group('param') is not None:
                g_fb_pwd = m.group('param')
    except IOError:
        print_to_log("You should define facebook email and password in %s." % (fb_filename))
        sys.exit()
    except:
        print_to_log("You should define facebook email and password in %s." % (fb_filename))
        sys.exit()

    ### Staus file
    try:
        ins = open( g_statusfilename, "r" )
        for line in ins:
            p = re.compile(r'^year_no=(?P<param2>\d+),post_no=(?P<param3>\d+),item_no=(?P<param4>\d+),com_name=(?P<param>.*)$')
            m = p.search( line.rstrip() )
            if m is not None and m.group('param') is not None:
                g_old_com_name = m.group('param')
                g_isfilevalid = True
                print_to_log("Last position - you scraped by this position.")
                print_to_log("before stock: "+str(g_old_com_name))
            if m is not None and m.group('param2') is not None:
                g_old_year_no = int(m.group('param2'))
                g_isfilevalid = True

                print_to_log("before year_no: "+str(g_old_year_no))
            if m is not None and m.group('param3') is not None:
                g_old_post_no = int(m.group('param3'))
                g_isfilevalid = True

                print_to_log("before post_no: "+str(g_old_post_no))
            if m is not None and m.group('param4') is not None:
                g_old_item_no = int(m.group('param4'))
                g_isfilevalid = True

                print_to_log("before item_no: "+str(g_old_item_no))
    except IOError:
        pass
    except:
        pass

    if g_isfilevalid == False:
    #already done or start from begin
        print_to_log("===============================================================================")
        print_to_log("<"+g_statusfilename+"> file stands for saving scraping staus. Don't touch this file!")
        print_to_log("Saving status into this file, scraper continues from the last position.")
        print_to_log("In the case when scraper is terminated unsuccessfully, scraper continues from the position in the next time.")
#        var = raw_input("Are you going to start scraping from begin?(yes/no):")
#    	if var.lower() != "yes" and var.lower() != "y":
#            sys.exit()
#        var = raw_input("Did you backup all xml file?(yes/no):")
#    	if var.lower() != "yes" and var.lower() != "y":
#            sys.exit()
            #remove all output files
        if os.path.exists(g_xmlfilename):
            os.remove(g_xmlfilename)

    #Start Crawler
    print_to_log("===================================================================================")
    print_to_log("crawler running...")

    if not os.path.exists(g_xmlfilename):
        #write to file
        fo = open(g_xmlfilename, "w")
        try:
            fo.write( '<?xml version="1.0" encoding="utf-8" ?><data></data>' )
        except IOError:
            pass
        except:
            pass
        fo.close()

    if fb_login() == 0:
#    if True:
        if g_stock_arg == "":
            #grab for all stocks
            com_list = readConfiguration()
            if len(g_old_com_name) > 0:
                #process from the last company
                process_one_company(g_old_com_name, com_list[g_old_com_name])
                pass

            for key, value in com_list.iteritems():
                #print "%s, %s" % (key, value)
                if key in g_processed_com_lst or key == g_old_com_name:
                    pass
                else:
                    process_one_company(key, value)
                    g_processed_com_lst.append(key)
                    #write to status file
                    fo = open(g_statusCompanyfilename, "wb")
                    strtmp = ""
                    for com in g_processed_com_lst:
                        strtmp += "%s\n" % com
                    fo.write( strtmp )
                    fo.close()
        else:
            #grab for one stock
            process_one_company(g_stock_arg, g_companyURL_arg)

    else:
        return

#        idx = 0
#        for seed in g_seeds:
#            if idx < g_old_com_no:
#                pass
#            else:
#                process_one_company(idx, seed[1], seed[2])

#            idx += 1

    #done successfully!
    print_to_log("===================================================================================")
    print_to_log("Congratulations! Scraping successfully finished!")
    print_to_log("===================================================================================")
    #os.remove(g_statusfilename)
    done_xmlfilename = "%s/fbComments_%s_%s_done.xml" % (g_output_xmls_folder, g_stock_arg, g_date_arg)
    done_statusfilename = "%s/status_%s_%s_done.txt" % (g_status_folder, g_stock_arg, g_date_arg)
    done_statusCompanyfilename = "%s/status_company_%s_done.txt" % (g_status_folder, g_date_arg)
    done_log_file = "%s/log_%s_%s_done.txt" % (g_log_folder, g_stock_arg, g_date_arg)

    os.rename(g_xmlfilename, done_xmlfilename)
    #os.rename(g_statusfilename, done_statusfilename)
    #os.rename(g_statusCompanyfilename, done_statusCompanyfilename)
    #os.rename(g_log_file, done_log_file)

    return

    #login
#    global g_browser
#    if fb_login() == 0:
#        one_com = "Microsoft"
#        com_url = "https://www.facebook.com/Microsoft"
#        process_one_company(one_com, com_url)

#    return

#    if fb_login() == 0:
        #one_url = "https://www.facebook.com/cocacola/timeline/2014"
#        one_url = "https://www.facebook.com/coca-cola/photos/a.10150567797523306.402510.40796308305/10153160523408306/?type=1&stream_ref=10"
#        one_url = "https://www.facebook.com/Microsoft/posts/10150175341308721?stream_ref=10"
#        one_com = "Microsoft"

#        process_one_page(one_com, one_url)
#        sys.exit()
#    else:
#        pass

if __name__ == "__main__":
    inputfile = ''
    outputfile = ''
    argv = sys.argv[1:]
    try:
        opts, args = getopt.getopt(argv, "d:s:u:", ["date=", "stock=", "url="])
    except getopt.GetoptError:
        #--date 20140416 --stock KO --url "https://www.facebook.com/cocacola"
        #-d 20140416 -s KO -u "https://www.facebook.com/cocacola"
        #--date 20140416 --stock MSFT --url "https://www.facebook.com/Microsoft"
        #-d 20140416 -s MSFT -u "https://www.facebook.com/Microsoft"
        print_to_log('ex) fbCommentShare-crawler.py -d 20140416 -s KO -u "https://www.facebook.com/cocacola"')
        print_to_log('    fbCommentShare-crawler.py --date 20140416 --stock KO --url "https://www.facebook.com/cocacola"')
        print_to_log('    fbCommentShare-crawler.py -d 20140416 -s MSFT -u "https://www.facebook.com/Microsoft"')
        print_to_log('    fbCommentShare-crawler.py --date 20140416 --stock MSFT --url "https://www.facebook.com/Microsoft"')
        sys.exit(2)
    for opt, arg in opts:
        if opt in ("-d", "--date"):
            g_date_arg = arg
        if opt in ("-s", "--stock"):
            g_stock_arg = arg
        if opt in ("-u", "--url"):
            g_companyURL_arg = arg
    print_to_log('Date is %s' % (g_date_arg))
    print_to_log('Stock is %s' % (g_stock_arg))
    print_to_log('Company URL is %s' % (g_companyURL_arg))

    if not os.path.exists(g_status_folder):
        os.makedirs(g_status_folder)
    if not os.path.exists(g_output_xmls_folder):
        os.makedirs(g_output_xmls_folder)
    if not os.path.exists(g_log_folder):
        os.makedirs(g_log_folder)

    g_xmlfilename = "%s/fbComments_%s_%s.xml" % (g_output_xmls_folder, g_stock_arg, g_date_arg)
    g_statusfilename = "%s/status_%s_%s.txt" % (g_status_folder, g_stock_arg, g_date_arg)
    g_statusCompanyfilename = "%s/status_company_%s.txt" % (g_status_folder, g_date_arg)
    g_log_file = "%s/log_%s_%s.txt" % (g_log_folder, g_stock_arg, g_date_arg)

    #is being run directly
    main()