import re
import requests
from collections import OrderedDict
from datetime import datetime
import config

def parse_template(template_file):
    template_channels = OrderedDict()
    current_category = None

    with open(template_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                if "#genre#" in line:
                    current_category = line.split(",")[0].strip()
                    template_channels[current_category] = []
                elif current_category:
                    channel_name = line.split(",")[0].strip()
                    template_channels[current_category].append(channel_name)

    return template_channels

def fetch_channels(url):
    channels = OrderedDict()

    try:
        response = requests.get(url)
        response.raise_for_status()
        response.encoding = 'utf-8'
        lines = response.text.split("\n")

        current_category = None

        if url.endswith(".m3u"):
            for line in lines:
                line = line.strip()
                if line.startswith("#EXTINF"):
                    match = re.search(r'group-title="(.*?)",(.*)', line)
                    if match:
                        current_category = match.group(1).strip()
                        channel_name = match.group(2).strip()
                        if current_category not in channels:
                            channels[current_category] = []
                elif line and not line.startswith("#"):
                    channel_url = line.strip()
                    if current_category and channel_name:
                        channels[current_category].append((channel_name, channel_url))
        else:
            for line in lines:
                line = line.strip()
                if "#genre#" in line:
                    current_category = line.split(",")[0].strip()
                    channels[current_category] = []
                elif current_category:
                    match = re.match(r"^(.*?),(.*?)$", line)
                    if match:
                        channel_name = match.group(1).strip()
                        channel_url = match.group(2).strip()
                        channels[current_category].append((channel_name, channel_url))
                    elif line:
                        channels[current_category].append((line, ''))
    except requests.RequestException as e:
        print(f"Failed to fetch channels from the URL: {url}, Error: {e}")

    return channels

def match_channels(template_channels, all_channels):
    matched_channels = OrderedDict()

    def has_two_common_chinese_chars(name1, name2):
        # 提取两个名称中的汉字
        chinese_chars_name1 = [char for char in name1 if '\u4e00' <= char <= '\u9fff']
        chinese_chars_name2 = [char for char in name2 if '\u4e00' <= char <= '\u9fff']
        # 找出两个名称中共同的汉字
        common_chars = set(chinese_chars_name1).intersection(set(chinese_chars_name2))
        # 如果共同汉字的数量大于或等于2，则返回True
        return len(common_chars) >= 2

    for online_category, online_channel_list in all_channels.items():
        for template_category, _ in template_channels.items():
            # 如果在线分类名称和模板分类名称至少有两个共同汉字，则认为它们匹配
            if has_two_common_chinese_chars(online_category, template_category):
                # 如果匹配，将在线分类的频道列表添加到匹配频道中
                matched_channels[online_category] = online_channel_list
                break  # 匹配后跳出内层循环

    return matched_channels





def filter_source_urls(template_file):
    template_channels = parse_template(template_file)
    source_urls = config.source_urls

    all_channels = OrderedDict()
    for url in source_urls:
        fetched_channels = fetch_channels(url)
        for category, channel_list in fetched_channels.items():
            if category in all_channels:
                all_channels[category].extend(channel_list)
            else:
                all_channels[category] = channel_list

    matched_channels = match_channels(template_channels, all_channels)

    return matched_channels, template_channels

def is_ipv6(url):
    return re.match(r'^http:\/\/\[[0-9a-fA-F:]+\]', url) is not None

def updateChannelUrlsM3U(channels, template_channels):
    written_urls = set()

    current_date = datetime.now().strftime("%Y-%m-%d")

    with open("live.m3u", "w", encoding="utf-8") as f_m3u:
        f_m3u.write("""#EXTM3U x-tvg-url="https://live.fanmingming.com/e.xml","http://epg.51zmt.top:8000/difang.xml","https://epg.v1.mk/fy.xml","http://epg.51zmt.top:8000/e.xml","https://epg.112114.xyz/pp.xml"\n""")
        f_m3u.write("""#EXTINF:-1 tvg-id="1" tvg-name="请阅读" tvg-logo="http://175.178.251.183:6689/LR.jpg" group-title="公告",请阅读\n""")
        f_m3u.write("https://liuliuliu.tv/api/channels/1997/stream\n")
        f_m3u.write("""#EXTINF:-1 tvg-id="1" tvg-name="yuanzl77.github.io" tvg-logo="http://175.178.251.183:6689/LR.jpg" group-title="公告",yuanzl77.github.io\n""")
        f_m3u.write("https://liuliuliu.tv/api/channels/233/stream\n")
        f_m3u.write("""#EXTINF:-1 tvg-id="1" tvg-name="更新日期" tvg-logo="http://175.178.251.183:6689/LR.jpg" group-title="公告",更新日期\n""")
        f_m3u.write("https://gitlab.com/lr77/IPTV/-/raw/main/%E4%B8%BB%E8%A7%92.mp4\n")
        f_m3u.write(f"""#EXTINF:-1 tvg-id="1" tvg-name="{current_date}" tvg-logo="http://175.178.251.183:6689/LR.jpg" group-title="公告",{current_date}\n""")
        f_m3u.write("https://gitlab.com/lr77/IPTV/-/raw/main/%E8%B5%B7%E9%A3%8E%E4%BA%86.mp4\n")

        with open("live.txt", "w", encoding="utf-8") as f_txt:
            for category, channel_list in template_channels.items():
                f_txt.write(f"{category},#genre#\n")
                if category in channels:
                    for channel_name in channel_list:
                        if channel_name in channels[category]:
                            sorted_urls = sorted(channels[category][channel_name], key=lambda url: not is_ipv6(url) if config.ip_version_priority == "ipv6" else is_ipv6(url))
                            line_number = 1
                            for url in sorted_urls:
                                if url and url not in written_urls and not any(blacklist in url for blacklist in config.url_blacklist):
                                    url_suffix = f"$IPV6『线路{line_number}』" if is_ipv6(url) else f"$IPV4『线路{line_number}』"
                                    if '$' in url:
                                        base_url = url.split('$', 1)[0]
                                    else:
                                        base_url = url
                                    
                                    new_url = f"{base_url}{url_suffix}"
                                    
                                    f_m3u.write(f"#EXTINF:-1 tvg-id=\"\" tvg-name=\"{channel_name}\" tvg-logo=\"https://gitee.com/yuanzl77/TVBox-logo/raw/main/png/{channel_name}.png\" group-title=\"{category}\",{channel_name}\n")
                                    f_m3u.write(new_url + "\n")
                                    f_txt.write(f"{channel_name},{new_url}\n")
                                    written_urls.add(url)
                                    line_number += 1

            f_txt.write("\n")

if __name__ == "__main__":
    template_file = "demo.txt"
    channels, template_channels = filter_source_urls(template_file)
    updateChannelUrlsM3U(channels, template_channels)
