import datetime
from sqlalchemy import Column, Date, ForeignKey, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine

Base = declarative_base()


# Adding Users to model
class User(Base):
  __tablename__ = 'user'

  id = Column(Integer, primary_key=True)
  name = Column(String(250), nullable=False)
  email = Column(String(250), nullable=False)
  picture = Column(String(250))


class Genre(Base):
  __tablename__ = 'genre'

  id = Column(Integer, primary_key=True)
  name = Column(String(250), nullable=False)

  @property
  def serialize(self):
    # Return object data in easily serializable format
    return {
        'id': self.id,
        'name': self.name,
    }


class Song(Base):
  __tablename__ = 'song'

  id = Column(Integer, primary_key=True)
  name = Column(String(250), nullable=False)
  artist_name = Column(String(250), nullable=False)
  # Will only be storing youtube video id, since there is a possiblty url
  # could change
  youtube_id = Column(String(250))
  date_added = Column(Date, default=datetime.datetime.now())
  # Linking Genre to song
  genre_id = Column(Integer, ForeignKey('genre.id'))
  genre = relationship(Genre)
  # Linking user to song
  user_id = Column(Integer, ForeignKey('user.id'))
  user = relationship(User)

  @property
  def serialize(self):
    """Return object data in easily serializeable format"""
    return {
        'id': self.id,
        'name': self.name,
        'artist_name': self.artist_name,
        'youtube_id': self.youtube_id,
        'date_added': self.date_added.isoformat(),
    }


engine = create_engine('postgresql://catalog:catalog@localhost/music')


Base.metadata.create_all(engine)
