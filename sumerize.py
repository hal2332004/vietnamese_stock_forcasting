# -*- coding: utf-8 -*-

# git clone https://huggingface.co/mr4/phobert-base-vi-sentiment-analysis
# git clone https://huggingface.co/danhtran2mind/viet-news-sum-mt5-small-finetune

import os
import torch
from transformers import T5ForConditionalGeneration, T5Tokenizer
from transformers import AutoTokenizer, AutoModelForSequenceClassification

model_summary_name = "danhtran2mind/viet-news-sum-mt5-small-finetune"
tokenizer_summary = T5Tokenizer.from_pretrained(model_summary_name)  
model_summary = T5ForConditionalGeneration.from_pretrained(model_summary_name)

model_sentiment_name = "mr4/phobert-base-vi-sentiment-analysis"
tokenizer_sentiment = AutoTokenizer.from_pretrained(model_sentiment_name)
model_sentiment = AutoModelForSequenceClassification.from_pretrained(model_sentiment_name)

def preprocess_input(text):
    inputs = tokenizer_summary(text, max_length=512, truncation=True, padding="max_length", return_tensors="pt")
    return inputs

def generate_summary(text):
    """
        Generate a summary of the given text using T5 model.
        
        Args:
            text (str): Input text to summarize
            
        Returns:
            str: Generated summary text
        """
    inputs = preprocess_input(text.replace("\n", ""))
    
    with torch.no_grad():
        summary_ids = model_summary.generate(
            inputs["input_ids"],
            attention_mask=inputs["attention_mask"],
            max_length=128, 
            early_stopping=True
        )
    summary = tokenizer_summary.decode(summary_ids[0], skip_special_tokens=True)
    return summary

def analyze_sentiment(text):
    """
        Analyze sentiment of the given text using PhoBERT model.
        
        Args:
            text (str): Input text to analyze sentiment
            
        Returns:
            dict: Dictionary containing sentiment labels and their corresponding scores
        """
    inputs = tokenizer_sentiment(text, padding=True, truncation=True, return_tensors="pt")
    outputs = model_sentiment(**inputs)
    predictions = torch.nn.functional.softmax(outputs.logits, dim=-1)
    sentiment_results = {}
    for i, prediction in enumerate(predictions):
        for j, value in enumerate(prediction):
            sentiment_results[model_sentiment.config.id2label[j]] = value.item()
    return sentiment_results

input_text = """Chị Thanh, gửi tiền tại Ngân hàng ACB chi nhánh An Lạc, quận Bình Tân (TP HCM), bình thường vẫn có thể rút tiền tại bất kỳ chi nhánh nào của ACB. Sáng nay cần tiền gấp, chị đã vào chi nhánh ACB Điện Biên Phủ để rút, song nhân viên tại đây thông báo hệ thống mạng gặp sự cố. Tạm thời ngân hàng chỉ giải quyết giao dịch cho những khách hàng đã gửi tiền tại chính chi nhánh này. Anh Minh Quang cho hay sáng nay anh chọn Ngân hàng Á Châu để gửi số tiền tiết kiệm, nhưng thấy hệ thống bị trục trặc nên đành ôm tiền về. "Thôi đành để hôm khác", anh nói. Trao đổi vớiVnExpress, ông Nguyễn Thanh Toại, Phó Tổng giám đốc Ngân hàng ACB thừa nhận sự cố mạng có xảy ra trong buổi sáng và cho hay, nguyên nhân do máy chủ gặp trục trặc. "Sáng nay khi khởi động, hệ thống mạng vẫn chạy bình thường. Song ít phút sau thì máy tính báo lỗi, các giao dịch online không thể thực hiện được. Hệ thống ATM cũng bị tê liệt hoàn toàn", ông Toại nói. Để ứng phó tạm thời, ngân hàng chỉ có thể giải quyết giao dịch cho những khách hàng rút tiền tại chính nơi mở tài khoản. Theo ông Toại, sự cố này khiến giao dịch của ACB giảm đi, song thiệt hại không nhiều. Phó Tổng giám đốc ACB cho biết thêm, trước đây, sự cố hệ thống mạng tương tự cũng đã xảy ra nhưng đều được khắc phục khá nhanh. Đây là lần xảy ra lâu nhất. Đến 10h30, nhân viên giao dịch các chi nhánh bắt đầu nhận chi trả cho khách nộp tiền tại chỗ. Những khách hàng khác thuộc dạng "vãng lai" đều được hẹn lại vào buổi chiều. Sáng nay, khách đến giao dịch tại Công ty chứng khoán ACBS trực thuộc ngân hàng Á Châu cũng gặp khó khăn trong những giao dịch liên quan đến tài khoản như việc kiểm tra số dư, rút và nộp tiền vào tài khoản. "Đối với những lệnh bán chứng khoán vẫn thực hiện bình thường, nhưng lệnh mua của khách hàng đã được ACBS chuyển thẳng lên nhân viên nhập lệnh tại Sở Giao dịch qua đường điện thoại", một nhân viên tại đây cho biết."""
summary = generate_summary(input_text)
print(f"Summary: {summary}")

sentiment_results = analyze_sentiment(summary)
print("Sentiment Analysis on Summary:")
for label, score in sentiment_results.items():
    print(f"    {label}: {score}")



