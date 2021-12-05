import threading
import traceback

from sqlalchemy.sql.sqltypes import BigInteger
from MetaButler.modules.sql import BASE, SESSION
from sqlalchemy import Column, String
from sqlalchemy.dialects import postgresql

class Metas(BASE):
	__tablename__ = "metas"

	user_id = Column(BigInteger, primary_key=True)
	role_name = Column(String(255))

	def __init__(self, user_id, role):
		self.user_id = user_id
		self.role_name = role

	def __repr__(self):
		return f"<meta {self.user_id} with role {self.role_name}>"

Metas.__table__.create(checkfirst=True)

def is_meta(user_id: int, role: str = None):
	with SESSION() as local_session:
		if role:
			return bool(local_session.query(Metas).get((user_id, role)))
		else:
			return bool(local_session.query(Metas).get(user_id))

def get_meta_role(user_id: int):
	with SESSION() as local_session:
		ret = local_session.query(Metas).get({"user_id": user_id})
		if ret:
			return ret.role_name
	return None

def get_metas(role: str = None):
	with SESSION() as local_session:
		if not role:
			return local_session.query(Metas).all()
		else:
			return local_session.query(Metas).filter(Metas.role_name == role).all()

def set_meta_role(user_id: int, role: str):
	with SESSION() as local_session:
		try:
			# Check if the user exists first and create them if they don't.
			ret = local_session.query(Metas).get({"user_id": user_id})
			if not ret:
				ret = Metas(user_id, role)
				local_session.add(ret)
			else:
				ret.role_name = role
			local_session.commit()
			local_session.flush()
		except Exception:
			traceback.print_exc()
			local_session.rollback()

def remove_meta(user_id: int):
	with SESSION() as local_session:
		try:
			ret = local_session.query(Metas).get({"user_id": user_id})
			if ret:
				local_session.delete(ret)
			local_session.commit()
		except Exception:
			traceback.print_exc()
			local_session.rollback()
