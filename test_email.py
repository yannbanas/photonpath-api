# test_email.py
import os
os.environ["RESEND_API_KEY"] = "re_gq2UvfbP_8yyTy6uw8ZW2oRVmht6btzJf"  # Mets ta vraie clé
os.environ["EMAIL_FROM"] = "PhotonPath <noreply@banastechnologie.cloud>"

from email_service import init_email_service

service = init_email_service()

# Test envoi
result = service.send_welcome_email("yannbanas@gmail.com", "pk_test_123456789")

print(f"Résultat: {'✅ Envoyé !' if result else '❌ Échec'}")