while read line; do
for i in `seq 1 $1`; do
echo -e "${line}" : $(curl -L -silent -o /dev/null -w "Connect: %{time_connect} TTFB: %{time_starttransfer} Total time: %{time_total} \n" "${line}");
done
done
