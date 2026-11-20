# ds_prog_final

githubのGoogle組織のリポジトリをスクレイピングし、リポジトリ名、言語、スター数をSQLIteに保存する

##　メモ
pip install requests beautifulsoup4
python scraping.py

実行すると保存したデータがSELECT文で表示される

１ページ取得するごとにtime.sleep(1)　
?page=N` でページを進め、新しいリポジトリがなくなった時点で終了
取得結果は 2947 件
