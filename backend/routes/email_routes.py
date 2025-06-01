from fastapi import APIRouter
from controllers import user_controller

router = APIRouter(prefix="/email", tags=["Register"])

router.post("/send-otp")(user_controller.send_otp)
router.post("/verify-otp")(user_controller.verify_otp)
router.post("/register")(user_controller.register)
router.post("/check-email")(user_controller.check_email)
router.post("/login")(user_controller.login)
router.post("/google-login")(user_controller.google_login)
router.get("/is-auth")(user_controller.is_auth)
router.get("/data")(user_controller.get_user_data)
