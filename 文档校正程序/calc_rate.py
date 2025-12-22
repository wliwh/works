import math
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib import font_manager, rcParams

def calculate_equal_principal_interest(principal, annual_rate, months):
    """
    Calculate monthly payment for equal principal and interest (等额本息) repayment
    
    Args:
        principal (float): Loan principal amount
        annual_rate (float): Annual interest rate (as decimal, e.g., 0.05 for 5%)
        months (int): Number of repayment months
    
    Returns:
        float: Monthly payment amount
    """
    # Convert annual rate to monthly
    monthly_rate = annual_rate / 12
    
    # Formula: M = P * [r(1+r)^n] / [(1+r)^n - 1]
    # M = monthly payment, P = principal, r = monthly rate, n = number of months
    if monthly_rate == 0:
        return principal / months
    
    numerator = monthly_rate * math.pow(1 + monthly_rate, months)
    denominator = math.pow(1 + monthly_rate, months) - 1
    
    monthly_payment = principal * (numerator / denominator)
    # [P · (1+r)^{k-1} – A · ((1+r)^{k-1} – 1)/r ] · r
    rs_monthly = [ monthly_rate*(principal * math.pow(1+monthly_rate, k) - monthly_payment*(math.pow(1+monthly_rate, k)-1)/monthly_rate) for k in range(months) ]
    # print(rs_monthly)
    return monthly_payment, rs_monthly


def calculate_equal_principal(principal, annual_rate, months):
    """
    Calculate monthly payments for equal principal (等额本金) repayment
    
    Args:
        principal (float): Loan principal amount
        annual_rate (float): Annual interest rate (as decimal, e.g., 0.05 for 5%)
        months (int): Number of repayment months
    
    Returns:
        list: List of monthly payment amounts
    """
    monthly_principal = principal / months
    monthly_rate = annual_rate / 12
    monthly_payments = []
    rs_monthly = []
    
    for month in range(1, months + 1):
        # Remaining principal after previous months
        remaining_principal = principal - (month - 1) * monthly_principal
        # Interest for the month
        monthly_interest = remaining_principal * monthly_rate
        # Total monthly payment (principal + interest)
        monthly_payment = monthly_principal + monthly_interest
        monthly_payments.append(monthly_payment)
        rs_monthly.append((principal-(month-1)*principal/months)*monthly_rate)
    
    return monthly_payments, rs_monthly


def get_repayment_details(principal, annual_rate, months, repayment_type):
    """
    Get repayment details based on the repayment type
    
    Args:
        principal (float): Loan principal amount
        annual_rate (float): Annual interest rate (as decimal)
        months (int): Number of repayment months
        repayment_type (str): "equal_interest" or "equal_principal"
    
    Returns:
        dict: Repayment details
    """
    if repayment_type == "equal_interest":
        monthly_payment, rs_monthly = calculate_equal_principal_interest(principal, annual_rate, months)
        total_payment = monthly_payment * months
        total_interest = total_payment - principal
        
        return {
            "monthly_payment": monthly_payment,
            "total_payment": total_payment,
            "total_interest": total_interest,
            "rs": rs_monthly
        }
    
    elif repayment_type == "equal_principal":
        monthly_payments, rs_monthly = calculate_equal_principal(principal, annual_rate, months)
        total_payment = sum(monthly_payments)
        total_interest = total_payment - principal
        
        return {
            "monthly_payment": monthly_payments[0],  # First month payment
            "total_payment": total_payment,
            "total_interest": total_interest,
            "rs": rs_monthly,
            # "breakdown": monthly_payments
        }
    
def calc_method2(principal, r1, paid_ym, all_months:int=12*30, method:str = 'bx'):
    paid_ym = paid_ym.replace('/','').replace('-','')
    months = 12*(int(paid_ym[:4])-2026) + int(paid_ym[4:6])+1
    principal = principal if principal > 10000 else principal*10000
    r1 = r1 if r1<0.06 else r1/100.0
    method = "equal_interest" if method=='bx' else "equal_principal"
    details = get_repayment_details(principal, r1, all_months, method)['rs']
    return f"{paid_ym[:4]}-{int(paid_ym[4:6])+1:02d}", months, sum(details[:months])


def calc_method1(principal, r2, ys=3):
    principal = principal if principal > 10000 else principal*10000
    r2 = r2 if r2<0.1 else r2/100.0
    return principal * r2 * ys


def plt_ratio():
    principal_amount = 10*10000  # Loan amount
    pay_interest_rate = 3 / 100.0  # 5% annual interest
    # repayment_months = 12*all_years  # 1 year

    font_path = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
    font = font_manager.FontProperties(fname=font_path)

    rcParams["font.family"] = font.get_name()
    rcParams["axes.unicode_minus"] = False  # 解决负号显示为方块的问题

    month_lst = [f"{y}-{m:02d}" for y in range(2026,2029) for m in range(1,13)]
    rate_lst = [x/100 for x in range(180, 265, 5)]
    data = [(m, r, calc_method1(principal_amount, r, 3)/calc_method2(principal_amount, 3.0, m, 5*12, 'bj')[-1]) for m in month_lst for r in rate_lst]
    data2 = [(m, r, calc_method1(principal_amount, r, 3)/calc_method2(principal_amount, pay_interest_rate, m, 30*12, 'bj')[-1]) for m in month_lst for r in rate_lst]

    df = pd.DataFrame(data, columns=['month', 'rate', 'ratio'])
    df = df.sort_values('month')          # 保证时间序
    df.month = pd.to_datetime(df['month'], format='%Y-%m')

    df2 = pd.DataFrame(data2, columns=['month', 'rate', 'ratio'])
    df2 = df2.sort_values('month')          # 保证时间序
    df2.month = pd.to_datetime(df2['month'], format='%Y-%m')

    # 2. 颜色：绿色>1，红色≤1
    colors = []
    # colors2 = np.where(df2.ratio > 1, 'green', 'orange')
    for n1,n2 in zip(df.ratio, df2.ratio):
        if n2>1:
            c = 'green'
        elif n1>1:
            c = 'orange'
        else:
            c = 'red'
        colors.append(c)
    colors = np.array(colors)

    # 3. 大小：与 |ratio-1| 成反比，远离 1 越大，接近 1 越小
    # 先算距离，再加个极小值防止除零，最后放大到合适像素区间
    dist = np.array([1/x if x<1 else x  for x in df.ratio])
    sizes = 10          # 300 可随意调，越大点越大
    # print(sizes)

    # 4. 画图
    plt.figure(figsize=(14, 6))
    # plt.scatter(df2.month, df2.rate, c=colors2, s=sizes, alpha=0.8, edgecolors='k', linewidth=0.3)
    plt.scatter(df.month, df.rate, c=colors, s=sizes, alpha=0.8, edgecolors='k', linewidth=0.3)

    # 参考线
    plt.axhline(y=1, color='gray', linestyle='--', linewidth=0.8)

    # 5. 格式
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    plt.gca().xaxis.set_major_locator(mdates.MonthLocator(interval=1))
    plt.ylim(1.75, 2.65)
    plt.xticks(rotation=60)
    plt.ylabel('存款利率%')
    plt.title('存款更优还是还贷更优')
    plt.tight_layout()

    plt.savefig('ratio_dots.png', dpi=300)
    # plt.show()
    
if __name__ == "__main__":
    # Example usage
    principal_amount = 10*10000  # Loan amount
    pay_interest_rate = 3 / 100.0  # 5% annual interest
    save_interest_rate = 2.0 / 100
    repayment_months = 12*5  # 1 year

    # print(calc_method2(principal_amount, pay_interest_rate, '2028-08', repayment_months, 'bj'), calc_method1(principal_amount, save_interest_rate))
    plt_ratio()