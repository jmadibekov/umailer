from sqlalchemy.orm import Session

from . import models, schemas


def get_email(db: Session, email_id: int):
    return db.query(models.Email).filter(models.Email.id == email_id).first()


def get_email_by_uid(db: Session, folder_name: str, uid: int):
    return (
        db.query(models.Email)
        .filter(models.Email.folder_name == folder_name, models.Email.uid == uid)
        .first()
    )


def create_email(db: Session, email: schemas.EmailCreate):
    db_email = models.Email(**email.dict())
    db.add(db_email)
    db.commit()
    db.refresh(db_email)
    return db_email


def create_email_attachment(
    db: Session, attachment: schemas.AttachmentCreate, email_id: int
):
    db_attachment = models.Attachment(**attachment.dict(), email_id=email_id)
    db.add(db_attachment)
    db.commit()
    db.refresh(db_attachment)
    return db_attachment
