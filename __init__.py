# /usr/bin/python3
"""
    fileListener
    监听某个文件夹,当文件夹内容出现修改时将修改的文件移动到指定的安全目录
    需要模块 : Flask watchdog

    设置详见: CONFIG.py


    当监测到新文件之后, 本程序将会将新创建的文件移动到指定位置
    同时将文件重命名为文件的MD5
    同时把文件的md5和原始文件名提交到指定地址
    发送数据格式:
    {
        fileName: 文件名
        md5:      文件md5
    }

    当服务器希望还原文件时, 向本程序的WEB服务器根目录 (监听地址和端口在 CONFIG.py 中设置)发送文件的MD5和文件名, 如果程序监测合格将会还原文件.
    地址例如: http://127.0.0.1:8080/ (post)
    提交数据格式:
    {
        fileName: 文件名
        md5:      文件md5
    }
    将会返回一个代码:
        200 - 成功
        500 - 错误
        400 - 没有找到相应文件
"""

from watchdog import events
from watchdog.observers import Observer
from urllib import request as request_
from urllib import parse
import time, os, hashlib, shutil, logging
import CONFIG


def move_file(path):
    """
    将文件移动至指定路径并且命名为随机 32 位字符,防止冲突
    :param path: 文件路径
    :return: fid 生成文件 32 位字符
    """
    if os.path.isdir(path): return  # 不对文件夹进行操作
    fileName = os.path.split(path)[1]

    if fileName.rfind("."):
        # 文件后缀
        fileSuffix = fileName[fileName.rfind("."):]
        if fileSuffix in CONFIG.PASS_SUFFIX:
            # 在后缀白名单内,放弃移动.
            return


    
    with open(path, 'rb') as fp:  # 获取md5
        md5 = hashlib.md5(fp.read()).hexdigest()
    
    if CONFIG.DEBUG :
        # 调试开关, 只发送数据不移动文件
        send_to_server(fileName, md5)
        return
    
    # 移动文件
    try:
        shutil.move(path, os.path.join(CONFIG.SAFELY_DIR, md5))
        send_to_server(fileName, md5)
    except Exception as e:
        logging.error("Move file error.", exc_info=e)


def send_to_server(fileName, md5):
    """
    将文件信息发送至服务器
    :param md5: 将文件信息发送到服务器
    :return:
    """

    data = bytes(parse.urlencode({"fileName": fileName, "md5": md5}), encoding='utf8')

    for i in range(5):  # 尝试五次
        try:
            request_.urlopen(CONFIG.POST_URL, data)
            break
        except Exception as e:
            logging.error("post data to server failed.", exc_info=e)



class FileHandler(events.FileSystemEventHandler):
    def on_modified(self, event):
        # 文件被修改
        move_file(event.src_path)

    def on_created(self, event):
        # 文件被创建
        move_file(event.src_path)


from flask import Flask, request

webApp = Flask (__name__)
@webApp.route("/", methods=["POST"])
def recover_file ():
    
    if request.form["md5"] in os.listdir (CONFIG.SAFELY_DIR):
        # 文件存在,移动之
        try:
            shutil.move (
                os.path.join (CONFIG.SAFELY_DIR,request.form["md5"]),
                os.path.join (CONFIG.LISTEN_DIR,request.form["fileName"])
            )
            return "200"
        except Exception as e:
            logging.error ("Move file error.",exc_info=e)
            return "500"
    else:
        return "400"  # 找不到文件

    

if __name__ == "__main__":
    event_handler = FileHandler()
    observer = Observer()
    observer.schedule(event_handler, CONFIG.LISTEN_DIR, recursive=True)
    observer.start()

    try:
        webApp.run (CONFIG.LISTEN_IP,CONFIG.SERVER_PORT)
    except Exception as e:
        observer.stop()
        logging.error ("There was some error that make this program shutdown.",exc_info=e)

    observer.join()
