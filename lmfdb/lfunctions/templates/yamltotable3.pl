#!/usr/bin/perl -w

######################
#
# yamltotable.prl
#
# convert yaml file with degree 3 data into htmltable
#
#######################

if($#ARGV != 1){
     die "\nThis program converts the degree 3 yaml file into an html table\n",
            "The syntax is:  \n\t yamltotable3.prl  inputfile outputfile\n\n"
} # ARGV if

my ($infile, $outfile) = ($ARGV[0],$ARGV[1]);

open(OUTFILE, ">$outfile") or die "the file $outfile can't be opened: $! \n";
#open(JUNKFILE, ">iiii") or die "the file $outfile can't be opened: $! \n";

open(INFILE, "<$infile") or die "the file $infile can't be opened: $! \n";


# my $urlheader="http://www.lmfdb.org/";
my $urlheader="/";

my $count=1;
my @otherlines=[];

$count=0;

        for(my $j=0;$j<=5;++$j) { $otherlines[$j]=""}
$line = <INFILE>;  # throw away first line

$rowfinished=0;
%rowvals=();

print OUTFILE qq|

<table border=1 cellpadding=5> 
<tbody>
<tr align="center">
<th align="center">First&nbsp;complex<br>critical&nbsp;zero</th>
<th align="center">{{ KNOWL('lfunction.underlying_object', title='underlying object') }}</th>
<th align="center">{{ KNOWL('lfunction.conductor', title='\$N\$') }}</th>
<th align="center">{{ KNOWL('lfunction.central_character', title='\$\\chi\$') }}</th>
<th align="center">{{ KNOWL('lfunction.arithmetic', title='arithmetic') }}</th>
<th align="center">{{ KNOWL('lfunction.self-dual', title='self-dual') }}</th>
<th align="center">\$\\delta,\\nu\$</th>
<th align="center">\$\\mu\$</th>
<th align="center">\$\\delta_1,\\delta_2,\\delta_3\$</th>
<th align="center">\$\\mu_1,\\mu_2\$</th>
<th align="center">{{ KNOWL('lfunction.sign', title='\$\\\\varepsilon\$') }}</th>
</tr>
|;

#read in row from file
while($line = <INFILE>) {

if($line =~ /XXXXXXXXXX/) {last}

chomp($line);
if(!$line) { next }

if($line =~/---/) {

printtofile(%rowvals);
%rowvals=()

}

else {

print($line);

# format of input file is entry1 : entry2
# entry1 is key; entry2 is value
$line =~ m/(.+) *\: *(.+)/;

$key=$1;
$val=$2;

print($key,"x   x",$val,"z\n");

#set value of key parameter in row
$rowvals{$key}=$val;


}

}

print OUTFILE "</tbody></table>\n";
print OUTFILE "\n{% endblock %}\n\n";
  
##############

sub printtofile {

my %rowvals=@_;

$multipleobject=0;

my $truesymbol = '&#10004;'; #"&#x25CF;";
my $falsesymbol = ''; #"&#x25CB;";

if(my $tmp=$rowvals{deltaRRR}) {

   $tmp =~s/\[//;
   $tmp =~s/\]//;

   $rowvals{deltaRRR}=$tmp;
}

if(my $tmp=$rowvals{muRRR}) {

   $tmp =~s/\[//;
   $tmp =~s/\]//;

   $rowvals{muRRR}=$tmp;
}

if(my $tmp=$rowvals{epsilon}) {

   if($tmp =~/e\((.*)\)/) {
     my $num =$1;
     $num=trimdigits($num);
     $rowvals{epsilon} = "\$e(".$num.")\$";
   }

}

if($rowvals{character} =~ /\.1 *$/) { $rowvals{character} = "1" }

if($rowvals{arithmetic} eq "true") { $rowvals{arithmetic}=$truesymbol }
else {$rowvals{arithmetic}=$falsesymbol }

if($rowvals{self_dual} eq "true") { $rowvals{self_dual}=$truesymbol }
else {$rowvals{self_dual}=$falsesymbol }

if($rowvals{object_name} =~ /\[/) {
  $multipleobject=1;
print("\n\nFOUND A MULTIPLE OBJECT\n\n");

  $tmpname = $rowvals{object_name};
  $tmpurl = $rowvals{object_url};

   $tmpname =~s/\[//;
   $tmpname =~s/\]//;
   $tmpurl =~s/\[//;
   $tmpurl =~s/\]//;

   @name=split(/,/,$tmpname);
   @url=split(/,/,$tmpurl);
}
  
print OUTFILE "<tr align=\"center\">";
if($rowvals{url}) {
  print OUTFILE "<td><a href=\"".$urlheader.$rowvals{url}."\">".trimdigits($rowvals{first_zero})."</a>"."</td>";
}
else {
  print OUTFILE "<td>".trimdigits($rowvals{first_zero})."</td>";
}

if($multipleobject) {
print OUTFILE "<td>";

$j=0;
print("\n\nSAVING A MULTIPLE OBJECT\n\n");

foreach $name (@name) {

print("\n\nOBJECT $j \n\n");

if($url[$j]) {
  print OUTFILE "<a href=\"".$urlheader.$url[$j]."\">".$name;
  if($j< (@name -1)) {
    print OUTFILE ",</a><br>";  # <br> needs some css styling
  }
  else { print OUTFILE "</a>" }
}

else {

  print OUTFILE $name;
  if($j< (@name -1)) {
    print OUTFILE ",<br>";  # <br> needs some css styling
  }
  else { print OUTFILE "</a>" }
}

++$j;

}
print OUTFILE "</td>";

}

else {
  if($rowvals{object_url}) {
print OUTFILE "<td>"."<a href=\"".$urlheader.$rowvals{object_url}."\">".$rowvals{object_name}."</a>"."</td>";
  }
  else {
print OUTFILE "<td>".$rowvals{object_name}."</td>";
  }
}

print OUTFILE "<td>".$rowvals{level}."</td>";
print OUTFILE "<td>".$rowvals{character}."</td>";
print OUTFILE "<td>".$rowvals{arithmetic}."</td>";
print OUTFILE "<td>".$rowvals{self_dual}."</td>";
if($rowvals{deltaRC}) {
print OUTFILE "<td>".$rowvals{deltaRC}.",".$rowvals{nuRC}."</td>";
}
else {
print OUTFILE "<td>"."</td>";
}
print OUTFILE "<td>".$rowvals{muRC}."</td>";
print OUTFILE "<td>".$rowvals{deltaRRR}."</td>";
print "About to trim digits from ",$rowvals{muRRR},"\n\n";
print OUTFILE "<td>".trimdigits($rowvals{muRRR})."</td>";
print OUTFILE "<td>".$rowvals{epsilon}."</td>";
print OUTFILE "<tr>\n";

# print OUTFILE "<td><a href=\"".$urlheader.$rowvals{url}."\">".$rowvals{Lfunction_texname}."</a>"."</td>";
#first_zero: 17.0249420759926
#Lfunction_texname: $L(s,f)$
#mu: 9.53369526135
#delta: [1,1]
#level: 1
#character: 1.1
#analytic_conductor: 0.3456789


}

##############

sub trimdigits {

my $num=shift;

#$num=($num || "");
$num="".$num;

print("MMMMM",$num,"NNNN");

if($num =~ /^[0-9]*$/) { print("\nMMMMM",$num,"NNNN\n"); return($num) }

if($num =~ /,/) {

@num = split(/,/,$num);
$ans = "";
foreach my $thenum (@num) {
   $ans = $ans.trimdigits($thenum).", "
}
$ans =~ s/, $//;

return($ans)
}

$num =~ s/^([0-9]*)\.([0-9]{0,5}).*/$1\.$2/;
#$num =~ s/([0-9]*)\.([0-9]{0,5})[0-9]*?/$1\.$2/;

return($num)


}
##############

sub ctsp {

my $ct= shift;

if($ct<10) { return("&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;")}

return("&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;")

}
