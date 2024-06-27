#!/usr/bin/expect

spawn scp -p -i /home/user/.ssh/id_rsa.dat [lindex $argv 0] [lindex $argv 1]
expect "*Enter passphrase for key*"
send "$env(FTP_SERVER_PASS_PHRASE)\r"
expect eof

