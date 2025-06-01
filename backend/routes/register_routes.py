from fastapi import APIRouter
from controllers import user_controller

router = APIRouter(prefix="/register", tags=["Register"])

router.post("/send-otp")(user_controller.send_otp)
router.post("/verify-otp")(user_controller.verify_otp)
