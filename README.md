# my_first_public_repo
# 新能源汽车出口贸易数据管理系统

## 📖 项目简介
本项目是一个基于 Python Flask 框架与 MySQL 数据库开发的 Web 数据管理系统。主要实现了新能源汽车出口贸易数据的录入、查询、可视化图表展示以及数据导出功能。

## 🛠️ 技术栈
- **后端**：Python 3 (Flask)
- **数据库**：MySQL
- **前端**：HTML, CSS, JavaScript, ECharts (如果有用图表的话)
- **版本控制**：Git, GitHub Desktop

## ✨ 核心功能
- 数据总览与统计图表
- 贸易数据多条件查询
- 数据字典维护
- 报表导出功能

## 🚀 如何本地运行
1. 克隆本项目到本地：
   ```bash
   git clone git@github.com:LeeSio25/nev-export-trade-system.git
2. 安装 Python 依赖：
    pip install -r requirements.txt
3. 配置数据库：将 sql语句 文件夹下的 .sql 脚本导入你的 MySQL。
    配置密码：复制 secrets_local.example.py 为 secrets_local.py，填入你的数据库密码。
4. 启动项目：
    python app.py
5. 在浏览器访问 http://127.0.0.1:5000 即可。