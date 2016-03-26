#!/usr/bin/perl -w

######################
#
# lamltotable.prl
#
# convert yaml file with degree 2 data into htmltable
#
#######################

if($#ARGV != 1){
     die "\nThis program converts the degree 2 yaml file into an html table\n",
            "The syntax is:  \n\t lamltotable.prl  inputfile outputfile\n\n"
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

<style type="text/css">
.ntdata .td { text-align: center;}
</style>


<table border=1 cellpadding=5> 
<tbody>
<tr align="center">
<td align="center">First&nbsp;complex<br>critical&nbsp;zero</td>
<td align="center">Underlying<br>object</td>
<td align="center">\$N\$</td>
<td align="center">\$\\chi\$</td>
<td align="center">arithmetic</td>
<td align="center">self-dual</td>
<td align="center">\$\\nu\$</td>
<td align="center">\$\\delta_1,\\delta_2\$</td>
<td align="center">\$\\mu\$</td>
<td align="center">\$\\varepsilon\$</td>
</tr>
|;


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

$line =~ m/(.+) *\: *(.+)/;

$key=$1;
$val=$2;

print($key,"x   x",$val,"z\n");

$rowvals{$key}=$val;


}

}

print OUTFILE "</tbody></table>\n";
  
##############

sub printtofile {

my %rowvals=@_;

$multipleobject=0;

my $truesymbol = "&#x25CF;";
my $falsesymbol = "&#x25CB;";

if(my $tmp=$rowvals{delta}) {

   $tmp =~s/\[//;
   $tmp =~s/\]//;

   $rowvals{delta}=$tmp;
}

if(my $tmp=$rowvals{epsilon}) {

   if($tmp =~/e\((.*)\)/) {
     my $num =$1;
     $num=trimdigits($num);
     $rowvals{epsilon} = "\$e(".$num.")\$";
   }

}

if($rowvals{character} =~ /\.1 *$/) { $rowvals{character} = "-" }

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
print OUTFILE "<td>".$rowvals{nu}."</td>";
print OUTFILE "<td>".$rowvals{delta}."</td>";
print OUTFILE "<td>".trimdigits($rowvals{mu})."</td>";
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

$num =~ s/^([0-9]*)\.([0-9]{0,5}).*/$1\.$2/;

return($num)


}
##############

sub ctsp {

my $ct= shift;

if($ct<10) { return("&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;")}

return("&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;")

}
