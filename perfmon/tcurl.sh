while read line; do
for i in `seq 1 $1`; do
curl -L  -silent -w "\nCurl URL %{url_effective}, HTTP status %{http_code}, Downloaded %{size_download} bytes, Total time %{time_total} secs\n" ${line} | grep -E '( [Ee]rror| [Pp]roblem|Curl)'
done
done
