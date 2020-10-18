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
        path:     完整文件名
    }

    当服务器希望还原文件时, 向本程序的WEB服务器根目录 (监听地址和端口在 CONFIG.py 中设置)发送文件的MD5和文件名, 如果程序监测合格将会还原文件.
    地址例如: http://127.0.0.1:8080/ (post)
    提交数据格式:
    {
        fileName: 文件名
        path:     完整文件名
        delete:   存在此项时将会删除文件
    }
    将会返回一个代码:
        200 - 成功
        300 - 成功移动文件,但是无法删除空文件夹
        400 - 没有找到相应文件
        500 - 错误
"""

from watchdog import events
from watchdog.observers import Observer
from urllib import request as request_
from urllib import parse
import os, hashlib, shutil, logging
import CONFIG

from flask import Flask, request

webApp = Flask(__name__)
WHITELIST = []  # 白名单,防止恢复后有又被移动


def move_file(path: str):
    """
    将文件移动至指定路径并且命名为随机 32 位字符,防止冲突
    :param path: 文件路径
    :return: fid 生成文件 32 位字符
    """

    if path in WHITELIST:  # 防止把恢复的文件也移动回去了.
        WHITELIST.remove(path)
        return

    if os.path.isdir(path): return  # 不对文件夹进行操作
    fileName = os.path.split(path)[1]

    if fileName.rfind("."):
        # 文件后缀
        fileSuffix = fileName[fileName.rfind("."):]
        if fileSuffix in CONFIG.PASS_SUFFIX:
            # 在后缀白名单内,放弃移动.
            return

    # with open(path, 'rb') as fp:  # 获取md5
    #     md5 = hashlib.md5(fp.read()).hexdigest()

    # 移动文件

    # CONFIG.LISTEN_DIR = '/www/wwwroot/listen'
    # CONFIG.SAFELY_DIR = '/www/wwwroot/safe'
    # path = '/www/wwwroot/listen/test/a.txt'
    # split_dir = ('/www/wwwroot/listen/test', 'a.txt')
    split_dir = os.path.split(path)
    # check_dir = '/www/wwwroot/safe/test'
    check_dir = split_dir[0].replace(CONFIG.LISTEN_DIR, CONFIG.SAFELY_DIR)
    # new_path = '/www/wwwroot/safe/test/xxx'
    new_path = os.path.join(check_dir, fileName)

    if CONFIG.DEBUG:
        # 调试开关, 只发送数据不移动文件
        send_to_server(fileName, new_path)
        return

    # 检查safe文件夹里是否存在相应子目录
    if check_dir != CONFIG.SAFELY_DIR:  # 如果有子文件夹
        try:
            os.makedirs(check_dir)  # 递归创建子文件夹
        except FileExistsError:
            # 文件夹已经存在.
            pass
        except Exception as e:
            # 其他错误
            logging.error("there is a error when moving the file.", exc_info=e)

    try:
        shutil.move(path, new_path)
        send_to_server(fileName, new_path)
    except Exception as e:
        logging.error("Move file error.", exc_info=e)


def send_to_server(fileName: str, path: str):
    """
    将文件信息发送至服务器
    :param fileName 文件名
    :param path     文件完整路径
    :return:
    """

    data = bytes(parse.urlencode({"fileName": fileName, "path": path}), encoding='utf8')

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


@webApp.route("/", methods=["POST"])
def recover_file():
    path: str = request.form["path"]  # 原文件完整路径
    safe_path: str = path.replace(CONFIG.LISTEN_DIR, CONFIG.SAFELY_DIR)
    if os.path.exists(safe_path):
        if "delete" in request.form:
            # 存在此键,删除文件
            try:
                os.remove(path)
                return "200"
            except Exception as e:
                logging.error("delete file failure.", exc_info=e)
                return "500"


        # 文件存在,移动之
        try:
            os.makedirs(os.path.split(path)[0])
            # 防止目标文件夹不存在
        except FileExistsError:
            # 已存在, 不管它
            pass
        except Exception as e:
            logging.error("make dirs error when recover file.", exc_info=e)

        try:
            WHITELIST.append(path)
            shutil.move(
                safe_path,
                path
            )
        except Exception as e:
            logging.error("Moving file failure.", exc_info=e)
            return "500"

        try:
            # 清除空文件夹
            check_dir = os.path.split(safe_path)[0]
            if not os.listdir(check_dir):
                try:
                    os.rmdir(check_dir)
                except Exception as e:
                    logging.error("remove empty dir error.", exc_info=e)
            return "200"
        except Exception as e:
            return "300"
    else:
        return "400"  # 找不到文件

if __name__ == "__main__":
    event_handler = FileHandler()
    observer = Observer()
    observer.schedule(event_handler, CONFIG.LISTEN_DIR, recursive=True)
    observer.start()

    try:
        webApp.run(CONFIG.LISTEN_IP, CONFIG.SERVER_PORT,
                   processes=1, threaded=False)
    except Exception as e:
        observer.stop()
        logging.error("There was some error that make this program shutdown.", exc_info=e)

    observer.join()
