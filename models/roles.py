from extensions import db
from enum import Enum

class RoleEnum(Enum):
    ADMIN = "Admin"
    CUSTOMER = "Customer"
    COMPANION = "Companion"

# Association table for Many-to-Many relationship between Roles and Permissions
role_permissions = db.Table('role_permissions',
    db.Column('role_id', db.Integer, db.ForeignKey('roles.role_id'), primary_key=True),
    db.Column('permission_id', db.Integer, db.ForeignKey('permissions.permission_id'), primary_key=True)
)

class Role(db.Model):
    __tablename__ = 'roles'
    role_id = db.Column(db.Integer, primary_key=True)
    role_name = db.Column(db.String(50), unique=True, nullable=False)

    # Relationship with User
    users = db.relationship('User', backref='role', lazy=True)
    
    # Relationship with Permission
    permissions = db.relationship('Permission', secondary=role_permissions, 
                                backref=db.backref('roles', lazy='dynamic'))

    def has_permission(self, permission_name):
        """Check if role has a specific permission by name"""
        return any(p.name == permission_name for p in self.permissions)

class Permission(db.Model):
    __tablename__ = 'permissions'
    permission_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    module = db.Column(db.String(50))
    action = db.Column(db.String(50))
    description = db.Column(db.String(255))

    def __repr__(self):
        return f'<Permission {self.name}>'