"""
配置文件
"""

if __name__ == '__main__':
    print("Please run '__init__.py' to start.")
    exit()

# 欲监听的文件夹 emp : "/www/webroot"
LISTEN_DIR = r"D:\杂项\fileListener\test"

# 欲临时存放的文件夹 emp: "/www/safely"
SAFELY_DIR = r"D:\杂项\fileListener\safety",
    
# 后缀白名单 , 不区分大小写
PASS_SUFFIX = ["jpg", "jpeg", "png", "gif", "webp", "tiff", "mp4", "flv"]

# 监听的服务器地址
LISTEN_IP = "0.0.0.0"
# 服务器端口
SERVER_PORT = 8080

# 接口地址 emp : "https://blog.m-jay.cn/"
POST_URL = ""

# 调试开关
DEBUG = False
