# T-103 標註規則（摘自 lexus_kit/label_with_gemini.py，內容未改動）

## 欄位定義（只需用到 relevant、sentiment、stance_to_dealer）

```python
class Label(BaseModel):
    relevant: bool = Field(description="是否實質討論 Lexus 售後：保養、維修、零件、保固、服務廠、服務顧問、技師、代步車。只是一句帶過則為 false")
    dealer_trust_issue: bool = Field(description="是否涉及對經銷商或原廠體系的信任問題，例如糾紛、詐騙、處理態度、被當盤子")
    speaker: Speaker = Field(description="發文者身分")
    purchase_type: str = Field(description="發文者是車主時才判斷：新車、二手；否則填不明")
    car_models: List[str] = Field(description="提到的 Lexus 車型，例如 ES300h、NX350h；沒有則空陣列")
    car_age_years: Optional[float] = Field(description="車齡（年），文中看不出則為 null")
    mileage_km: Optional[int] = Field(description="里程數（公里），文中看不出則為 null")
    topics: List[Topic]
    sentiment: str = Field(description="對 Lexus 售後的整體情緒：正面、中立、負面")
    stance_to_dealer: Stance = Field(description="發文者對原廠保修的立場")
    experience_at: str = Field(description="文中描述的保養維修經驗發生在哪裡：原廠、外廠、兩者都有、不明")
    pain_points: List[str] = Field(description="對保養維修的具體不滿（不論原廠或外廠），每點 15 字以內，最多 3 點，例如：等待太久、價格偏高、說明不清楚；沒有則空陣列")
    alternatives: List[Alternative] = Field(description="提到的替代選項")
    key_concerns: List[str] = Field(description="最在意的點，每點 15 字以內，最多 3 點")
    churn_reasons: List[str] = Field(description="若有猶豫或離開原廠，原因為何，每點 15 字以內；沒有則空陣列")
    comment_consensus: str = Field(description="推文的主流意見，一句話；沒有推文則空字串")
    comments_churned: int = Field(description="推文中有幾則是網友說自己已改去非原廠保養維修")
    comments_loyal: int = Field(description="推文中有幾則是網友說自己一直回原廠保養維修")
    comment_churn_reasons: List[str] = Field(description="推文中網友說離開原廠的原因，每點 15 字以內，最多 3 點；沒有則空陣列")
    evidence_quote: str = Field(description="最能代表立場的一句原文，40 字以內")
    summary: str = Field(description="一句話摘要，40 字以內")
```

## 判斷規則

規則：
- 只根據文中內容判斷，看不出來就填「不明」、null 或空陣列，不要猜。
- 回文中引用別人的文字已經移除，只根據回文者自己寫的內容判斷。
- relevant：內文「或推文」中有具體的售後內容就算 true，例如保養維修經驗、具體保養費用金額、
  零件通病或待料、保固或配件保固爭議、服務廠比較。文章主題是購車或新車菜單也一樣，只要推文有這類具體內容就算。
  只有泛泛一句「保養便宜」「很省心」、或完全沒有售後內容的品牌定位、新聞、購車金流糾紛，填 false。
- dealer_trust_issue：對經銷商或原廠體系的信任問題（糾紛、詐騙、處理態度、怕被當盤子）填 true，購車或售後皆可。
- 「原廠」包含 Lexus 授權經銷商的服務廠，例如北都汽車、國都汽車。
  在不同授權經銷商之間比較或換一家，不算離開原廠；只有改去非授權的保養廠、連鎖店或自行保養才算。
- stance_to_dealer（發文者對原廠保養維修的立場）：
  - 只有發文者是現任車主或前車主、且談到自己的保養維修去處時，才填忠誠、猶豫或已轉外廠。
  - 潛在買家、非車主一律填「未提及」。
  - 對購車過程或經銷商糾紛的不滿，不算保養維修立場，填「未提及」，改用 dealer_trust_issue 表達。
  - 「已轉外廠」：明確說自己已改去非原廠保養維修。
  - 「猶豫」：正在比較原廠與外廠、詢問外廠、抱怨原廠保養並考慮離開。
  - 「忠誠」：明確說會繼續或一直在原廠保養維修。
- experience_at：判斷文中描述的保養維修經驗發生地點。
  提到經銷商名稱（北都、國都等）、服務專員、預約進廠、代步車、保固內維修、原廠，通常是「原廠」；
  提到外面的保養廠、連鎖店、自己換，是「外廠」；完全看不出來填「不明」，不要猜。
- pain_points：只要有對保養維修的具體不滿就填，不需要表明要離開原廠，例如「保養等很久」「不便宜」。
- alternatives：只填「保養維修的替代地點或方式」。購車時比較其他品牌不算。
  「換其他品牌」只用在車主因售後經驗表示下次不買 Lexus。
- 推文代表其他網友意見：發文者立場以內文為主；推文的主流意見寫在 comment_consensus，
  推文中自述已改去外廠或一直回原廠的則數，分別寫在 comments_churned、comments_loyal。
