onerror { quit -code 1; }
do tcl_file.tcl

run -all
quit -code [expr [coverage attribute -name TESTSTATUS -concise] >= 2 ? [coverage attribute -name TESTSTATUS -concise] : 0]
exit

