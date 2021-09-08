cp -f .env.aapanel .env

curl https://getcomposer.org/download/2.0.13/composer.phar > composer.phar

php composer.phar install
php artisan key:gen

(cat <<EOF
[program:$1]
command=php artisan horizon
directory=$(pwd)
autorestart=true
startsecs=3
startretries=3
stdout_logfile=/www/server/panel/plugin/supervisor/log/$1.out.log
stderr_logfile=/www/server/panel/plugin/supervisor/log/$1.err.log
stdout_logfile_maxbytes=2MB
stderr_logfile_maxbytes=2MB
user=www
priority=999
numprocs=1
process_name=%(program_name)s_%(process_num)02d
EOF
) > /www/server/panel/plugin/supervisor/profile/$1.ini
