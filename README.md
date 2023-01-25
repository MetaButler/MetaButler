# MetaButler

![](images/metabutler.jpeg)

A modular telegram Python bot running on python3 with an sqlalchemy database.

Originally a Kigyo fork - 

Can be found on telegram as [MetaButler](https://t.me/MetaButlerBot).

The Support group can be reached out to at [MetaButler](https://t.me/MetaProjectsSupport), where you can ask for help setting up your bot, discover/request new features, report bugs, and stay in the loop whenever a new update is available.



## Setting up the bot (Read this before trying to use!):


# How to setup

- `clone this repository`
- `cd MetaButler`
- `cp sample_config.ini config.ini`
- *Fill in all the vars*
- `cp alembic_sample.ini alembic.ini`
- *Fill in sqlalchemy.url var (L#55) with the same value as SQLALCHEMY_DATABASE_URI from config.ini*
- `pip3 install -U -r requirements.txt`
- *The following step is important, it introduces a new column to blacklist table:*
- `alembic upgrade head`
- *And finally* `python3 -m MetaButler`

*Enjoy!*

# How can I obtain `bot_token`?

Just talk to [BotFather](https://t.me/BotFather)(described [here](https://core.telegram.org/bots#6-botfather))
and follow a few simple steps. Once you've created a bot and received your
authorization token, that's it! that's your `bot_token`.

# How can I obtain a `api_key` and `api_hash`?

In order to obtain an API key and hash you need to do the following:

 - Sign up for Telegram using any application.
 - Login to your Telegram core: [https://my.telegram.org](https://my.telegram.org).
 - Go to '[API Development tools](https://my.telegram.org/apps)' and fill out the form.
 - You will get basic addresses as well as the `api_id` and `api_hash` parameters
   required for Metabutler's configuration file.

# Database

If you wish to use a database-dependent module(eg: locks, notes, userinfo, users, filters, welcomes),
you'll need to have a database installed on your system. I use postgres, so I recommend using it for optimal compatibility.

In the case of postgres, this is how you would set up a the database on a debian/ubuntu system. Other distributions may vary.

- install postgresql:

`sudo apt-get update && sudo apt-get install postgresql`

- change to the postgres user:

`sudo su - postgres`

- create a new database user(change YOUR_USER appropriately):

`createuser -P -s -e YOUR_USER`

This will be followed by you needing to input your password.

- create a new database table:

`createdb -O YOUR_USER YOUR_DB_NAME`

Change YOUR_USER and YOUR_DB_NAME appropriately.

- finally:

`psql YOUR_DB_NAME -h YOUR_HOST YOUR_USER`

This will allow you to connect to your database via your terminal.
By default, YOUR_HOST should be 0.0.0.0:5432.

You should now be able to build your database URI. This will be:

`sqldbtype://username:pw@hostname:port/db_name`

Replace sqldbtype with whichever db youre using(eg postgres, mysql, sqllite, etc)
repeat for your username, password, hostname(localhost?), port(5432?), and db name.

## Credits
The bot is based of on the original work done by
 - [PaulSonOfLars](https://github.com/PaulSonOfLars)
# Thanks to
 - [Dank-del](https://github.com/Dank-del)
 - [SoapDev](https://github.com/SoapDev2018)
 - And many more that we couldn't list it here!
