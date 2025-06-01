from fastapi import APIRouter
from fastapi import Request
from controllers import sentiment_controller

router = APIRouter(tags=["Analyze"])

router.post("/analyze")(sentiment_controller.analyze_sentiment)
router.delete("/delete/{id}")(sentiment_controller.delete_analysis)


router.get("/getdata")(sentiment_controller.get_user_analysis)

