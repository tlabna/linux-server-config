# Linux Server Configuration Project

**Goal**: You will take a baseline installation of a Linux distribution on a virtual machine and prepare it to host your web applications, to include installing updates, securing it from a number of attack vectors and installing/configuring web and database servers. A deep understanding of exactly what your web applications are doing, how they are hosted, and the interactions between multiple systems are what define you as a Full Stack Web Developer. In this project, you’ll be responsible for turning a brand-new, bare bones, Linux server into the secure and efficient web application host your applications need.

### Server Details

IP address: `54.91.117.82`

SSH port: `2200`

URL: `http://ec2-54-91-117-82.compute-1.amazonaws.com/`
[found my submitting IP to this website](http://ping.eu/rev-lookup/)

## Steps to add User, enable SSH and disable root login

### Add User and enable SSH

1. `sudo adduser grader`
2. Give user sudo permission `sudo visudo`. [Follow steps here](https://www.digitalocean.com/community/tutorials/how-to-add-and-delete-users-on-an-ubuntu-14-04-vps)
3. On local machone type `ssh-keygen` to generate keys. Follow prompts and save files appropriately
4. Login as grader on VM. `sudo login grader`
5. create ssh directory. `mkdir ~/.ssh`
6. create file `touch ~/.ssh/authorized_keys`
7. copy contents of your public key saved on your local machine and paste into the file create in step 6. `sudo nano ~/.ssh/authorized_keys`
8. You can now ssh into Amazon VM from your local machine using `ssh grader@Your-IP-Address -i ~/.ssh/your-ssh-private-key-filename`

[More info on above steps here](https://docs.google.com/document/d/1pvE6os2ctLevO_EBmg3Leq4VEc1DbORcxQ_zpPqVr78/edit)

### Disable root login

1. Open file `sudo nano /etc/ssh/sshd_config`
2. Edit line `PermitRootLogin without-password` to `PermitRootLogin no`


## Steps taken to configure server

### 1. Update all currently installed packages

`sudo apt-get update`

### 2. Configure the Uncomplicated Firewall (UFW) to only allow incoming connections for SSH (port 2200), HTTP (port 80), and NTP (port 123)

1. Deny all incoming requests `sudo ufw default deny incoming`
2. Allow all outgoing requests `sudo ufw default allow outgoing`
3. Allow ssh through port 2200 `sudo ufw allow 2200/tcp`
4. Allow http though port 80 `sudo ufw allow www` or `sudo ufw allow 80/tcp`
5. allow NTP through port 123 `sudo ufw allow ntp` or `sudo ufw allow 123/udp`
6. Turn on firewall `sudo ufw enable`

`sudo ufw status` to confirm rules

Source: [ufw essentials](https://www.digitalocean.com/community/tutorials/ufw-essentials-common-firewall-rules-and-commands)

### 3. Change the SSH port from 22 to 2200

1. Open sshd config file `sudo nano /etc/ssh/sshd_config`
2. Change `Port 22` to `Port 2200` save and exit

### 4. Configure the local timezone to UTC

`sudo dpkg-reconfigure tzdata` and follow prompts by selecting correct geographical region

[Source](https://www.digitalocean.com/community/tutorials/additional-recommended-steps-for-new-ubuntu-14-04-servers#configure-timezones-and-network-time-protocol-synchronization)

### 5. Install and configure Apache to serve a Python mod_wsgi application

1. `sudo apt-get install apache2`
2. `sudo apt-get install libapache2-mod-wsgi`

### 6. Install and configure PostgreSQL

1. `sudo apt-get install postgresql postgresql-contrib`
2. Add user for the database to be created. `sudo -u postgres createuser --interactive`
Here, was asked multiple questions which I answered no to all to give user (named: catalog) limited permissions.

```
Shall the new role be a superuser? (y/n)
Shall the new role be allowed to create database? (y/n)
Shall the new role be allowed to create more new roles? (y/n)
```

Next create database **music** for catalog user.

```
$ sudo -i -u postgres
$ psql
postgres$ CREATE DATABASE music WITH OWNER catalog;

We can now connect to the database and lock down the permissions to only let "catalog" create tables:

postgres$ \c demo_application
postgres$ REVOKE ALL ON SCHEMA public FROM public;
postgres$ GRANT ALL ON SCHEMA public TO catalog;
```

At this point, I wanted to make sure that remote connections are not allowed to the database. We need to check the file below.

`sudo nano /etc/postgresql/9.1/main/pg_hba.conf`

As you can see below we can confirm that the only connections are from localhost.

```
local   all             postgres                                peer
local   all             all                                     peer
host    all             all             127.0.0.1/32            md5
host    all             all             ::1/128                 md5
```

### 7. Install git

1. Follow setps shown [here](https://www.digitalocean.com/community/tutorials/how-to-install-git-on-ubuntu-14-04#how-to-set-up-git) and configure.

### 8. Deploy the Item Catalog project.

###### Clone repo and download dependencies needed

1. Cloned Item catalog project to `/var/www/item-catalog/`
2. Moved catalog directory to `/var/www/item-catalog/`
3. Install Flask, SQLAlchemy and dependencies.

```
$ sudo apt-get install python-pip python-psycopg2 python-flask python-sqlalchemy
$ sudo pip install oauth2client
$ sudo pip install requests
$ sudo pip install httplib2
```

###### Changes to catalog files that are necessary for app to run error free

1. Change urls to correctly point to local database. Files that needed changes: **database_setup.py**, **dummy_data.py**, **main.py** (NOTE. This file got renamed to **__init__.py** to work with WSGI).
New url `create_engine('postgresql://catalog:catalog@localhost/music')`

2. To be able to read files **client_secrets.py** and **fb_client_secrets.py**, changes are needed in the code since current working directory of the python app running through WSGI is not necessarily the one where the python files are stored. Therefore, in the renamed file **__init__.py** (formerly main.py) these changes where necessary:

- Add `import os`
- Add line `app_dir = os.path.dirname(__file__)`
- Change lines calling both client secrets files (4 total, 2 google, 2 facebook)

```
1. CLIENT_ID = json.loads(
    open(app_dir + '/client_secrets.json', 'r').read())['web']['client_id']

2. oauth_flow = flow_from_clientsecrets(app_dir + '/client_secrets.json', scope='')

3. app_id = json.loads(open(app_dir + '/fb_client_secrets.json', 'r').read())[
        'web']['app_id']

4. app_secret = json.loads(
        open(app_dir + '/fb_client_secrets.json', 'r').read())['web']['app_secret']
```

**Note.** It was extremely important to change urls in both Google and Facebook developer consoles to allow redirects and authorization from the new URL posted above. Without doing this Google and Facebook would not trust requests coming from `http://ec2-54-91-117-82.compute-1.amazonaws.com`

###### Configure & enable a new virtual host.

[Follow steps here](https://www.digitalocean.com/community/tutorials/how-to-deploy-a-flask-application-on-an-ubuntu-vps)

`$ sudo nano /etc/apache2/site-available/catalog.conf`

Add and save:

```
<VirtualHost *:80>
                ServerName 54.91.117.82
                ServerAdmin tlabna@gmail.com
                WSGIScriptAlias / /var/www/item-catalog/catalog.wsgi
                <Directory /var/www/item-catalog/catalog/>
                        Order allow,deny
                        Allow from all
                </Directory>
                Alias /static /var/www/item-catalog/catalog/static
                <Directory /var/www/item-catalog/catalog/static/>
                        Order allow,deny
                        Allow from all
                </Directory>
                ErrorLog ${APACHE_LOG_DIR}/error.log
                LogLevel warn
                CustomLog ${APACHE_LOG_DIR}/access.log combined
</VirtualHost>
```

`$ sudo a2ensite catalog`

###### Create .wsgi file.

`$ sudo nano /var/www/item-catalog/catalog.wsgi`

Add and save:

```
#!/usr/bin/python
import sys
import logging
logging.basicConfig(stream=sys.stderr)
sys.path.insert(0,"/var/www/item-catalog/")

from catalog import app as application
application.secret_key = 'super_secret_key'
```


###### Final step

Restart Apache `sudo service apache2 restart`

Item catalog should now be deplyed and running.
