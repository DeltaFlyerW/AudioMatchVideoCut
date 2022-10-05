# AudioMatchVideoCut
Matching video clips by audio features. 
If cupy is installed, the script will use GPU to parse audio features.
Otherwise using scipy to do that with single CPU thread. This script is depent on https://github.com/worldveil/dejavu.
## Install

```bash
pip install moviepy
```


## Usage

```python
from audioMatch import VideoAudio

originVideoPath = "video.mkv"
clipAudioPath  ="audio.mp3"

result = VideoAudio().match(originVideoPath , clipAudioPath)


```


## 匹配BiliBili视频删减方法

1.下载Release中附件的biliMatch.7z并解压

2.下载原版视频与删减版视频, 可以为单个视频文件,如"魔法纪录 魔法少女小圆外传 - 10.我的名字(Av94297942,P10).mp4",
或将B站app中的缓存文件夹,如"/storage/emulated/0/Android/data/tv.danmaku.bili/download/s_41483/478573", 复制到电脑上

3.运行biliMatch文件夹下的biliMatch.exe ,输入两个视频或视频文件夹的路径

4.若删减版视频为缓存文件夹, 或有同名弹幕文件在同一文件夹下, 会根据匹配结果生成一个完整版弹幕文件, 否则生成一个删减匹配结果文件

P.S. 默认情况下, 匹配结果同时也会上传至服务器, 用于弹幕扩展程序加载内地弹幕, 可在biliMatch/data/config.json中更改这一设置.
