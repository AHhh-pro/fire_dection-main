#!/usr/bin/env python3
"""
测试温度HTTP服务器
"""
import json
import urllib.request
import urllib.error

def test_temperature_server():
    """测试向本地服务器发送温度数据"""
    url = "http://localhost:8090"
    
    # 测试数据
    temperature_data = {
        "sensorId": 1,
        "value": 35.5
    }
    
    try:
        # 准备请求
        data = json.dumps(temperature_data).encode('utf-8')
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                'Content-Type': 'application/json',
                'Content-Length': len(data)
            },
            method='POST'
        )
        
        # 发送请求
        print(f"正在发送温度数据到 {url}...")
        print(f"数据: {temperature_data}")
        
        with urllib.request.urlopen(req, timeout=5) as response:
            result = response.read().decode('utf-8')
            print(f"服务器响应: {result}")
            print("✓ 测试成功！")
            return True
            
    except urllib.error.URLError as e:
        print(f"✗ 连接失败: {e}")
        print("\n可能的原因:")
        print("1. Python GUI程序没有运行")
        print("2. 端口8090被其他程序占用")
        print("3. 防火墙阻止了连接")
        return False
    except Exception as e:
        print(f"✗ 错误: {e}")
        return False

if __name__ == "__main__":
    test_temperature_server()
