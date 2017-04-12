from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database_setup import Genre, Base, Song, User

engine = create_engine('postgresql://catalog:catalog@localhost/music')
# Bind the engine to the metadata of the Base class so that the
# declaratives can be accessed through a DBSession instance
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
# A DBSession() instance establishes all conversations with the database
# and represents a "staging zone" for all the objects loaded into the
# database session object. Any change made against the objects in the
# session won't be persisted into the database until you call
# session.commit(). If you're not happy about the changes, you can
# revert all of them back to the last commit by calling
# session.rollback()
session = DBSession()


# Create dummy user
user1 = User(name="Robo Barista", email="robbar@udacity.com",
             picture='https://pbs.twimg.com/profile_images/2671170543/18debd694829ed78203a5a36dd364160_400x400.png')
session.add(user1)
session.commit()


# Genres
genre1 = Genre(name="Jazz")

session.add(genre1)
session.commit()

genre2 = Genre(name="Hip Hop")

session.add(genre2)
session.commit()

genre3 = Genre(name="Pop")

session.add(genre3)
session.commit()

genre4 = Genre(name="Rock")

session.add(genre4)
session.commit()

genre5 = Genre(name="Country")

session.add(genre5)
session.commit()


# Songs
song1 = Song(name="Morning Call", artist_name="Nick Colionne",
             youtube_id="QsuZPScE5uc", genre=genre1, user=user1)


session.add(song1)
session.commit()

song2 = Song(name="Black Beatles", artist_name="Rae Sremmurd",
             youtube_id="b8m9zhNAgKs", genre=genre2, user=user1)


session.add(song2)
session.commit()

song3 = Song(name="Shape of You", artist_name="Ed Sheeran",
             youtube_id="JGwWNGJdvx8", genre=genre3, user=user1)


session.add(song3)
session.commit()

song4 = Song(name="Stairway to Heaven", artist_name="Led Zeppelin",
             youtube_id="IS6n2Hx9Ykk", genre=genre4, user=user1)


session.add(song4)
session.commit()

song4 = Song(name="Body Like a Back Road", artist_name="Sam Hunt",
             youtube_id="Mdh2p03cRfw", genre=genre5, user=user1)


session.add(song4)
session.commit()

print "Adding dummy data complete! =)"
