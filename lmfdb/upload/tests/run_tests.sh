for file in test* ; do
  echo Testing $file
  sage -python ../fileformats.py $file
  echo
done
