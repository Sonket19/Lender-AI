import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException
from config.settings import settings

async def send_interview_email(to_email: str, founder_name: str, interview_link: str, deal_id: str, missing_count: int):
    """Send interview invitation email to founder using Brevo"""
    
    # Configure Brevo API
    configuration = sib_api_v3_sdk.Configuration()
    configuration.api_key['api-key'] = settings.BREVO_API_KEY
    
    api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))
    
    # Email content
    subject = "Quick Chat About Your Startup - Investment Review"
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
        <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f3f4f6; padding: 40px 20px;">
            <tr>
                <td align="center">
                    <table width="600" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border-radius: 12px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);">
                        <tr>
                            <td style="padding: 40px 40px 20px 40px;">
                                <h1 style="margin: 0; color: #1f2937; font-size: 28px; font-weight: 700;">
                                    Hi {founder_name}! 👋
                                </h1>
                            </td>
                        </tr>
                        <tr>
                            <td style="padding: 0 40px 20px 40px;">
                                <p style="margin: 0 0 20px 0; color: #4b5563; font-size: 16px; line-height: 1.6;">
                                    Thank you for sharing your pitch deck with us. We're excited about what you're building!
                                </p>
                                <p style="margin: 0 0 20px 0; color: #4b5563; font-size: 16px; line-height: 1.6;">
                                    We'd love to learn a bit more to complete our investment analysis. We've set up an AI-powered conversation that will ask you <strong>{missing_count} quick questions</strong>.
                                </p>
                            </td>
                        </tr>
                        <tr>
                            <td style="padding: 0 40px 30px 40px;">
                                <table width="100%" cellpadding="20" cellspacing="0" style="background-color: #eff6ff; border-radius: 8px; border-left: 4px solid #3b82f6;">
                                    <tr>
                                        <td>
                                            <p style="margin: 0 0 10px 0; color: #1e40af; font-size: 14px; font-weight: 600;">
                                                What to expect:
                                            </p>
                                            <ul style="margin: 0; padding-left: 20px; color: #1e40af; font-size: 14px; line-height: 1.8;">
                                                <li>5-10 minute conversation</li>
                                                <li>Natural, friendly AI chat</li>
                                                <li>Text or voice responses supported</li>
                                                <li>One-time secure link</li>
                                            </ul>
                                        </td>
                                    </tr>
                                </table>
                            </td>
                        </tr>
                        <tr>
                            <td align="center" style="padding: 0 40px 40px 40px;">
                                <a href="{interview_link}" 
                                   style="display: inline-block; background-color: #3b82f6; color: #ffffff; padding: 16px 40px; text-decoration: none; border-radius: 8px; font-weight: 600; font-size: 16px;">
                                    Start Conversation →
                                </a>
                            </td>
                        </tr>
                        <tr>
                            <td style="padding: 0 40px 40px 40px; border-top: 1px solid #e5e7eb;">
                                <p style="margin: 20px 0 0 0; color: #6b7280; font-size: 13px; line-height: 1.6;">
                                    <strong>Note:</strong> This link is for one-time use and will expire in 7 days.
                                </p>
                            </td>
                        </tr>
                        <tr>
                            <td style="padding: 0 40px 40px 40px;">
                                <p style="margin: 0; color: #4b5563; font-size: 16px;">
                                    Best regards,<br>
                                    <strong>Investment Team</strong>
                                </p>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """
    
    # Create email object
    send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
        to=[{"email": to_email, "name": founder_name}],
        sender={"email": settings.FROM_EMAIL, "name": "Investment Team"},
        subject=subject,
        html_content=html_content
    )
    
    try:
        # Send email
        api_response = api_instance.send_transac_email(send_smtp_email)
        return True
    except ApiException as e:
        raise Exception(f"Failed to send email: {str(e)}")

async def send_verification_email(to_email: str, code: str):
    """Send verification code email using Brevo"""
    
    # Configure Brevo API
    configuration = sib_api_v3_sdk.Configuration()
    configuration.api_key['api-key'] = settings.BREVO_API_KEY
    
    api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))
    
    # Email content
    subject = f"Your Verification Code: {code}"
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
        <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f3f4f6; padding: 40px 20px;">
            <tr>
                <td align="center">
                    <table width="600" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border-radius: 12px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);">
                        <tr>
                            <td style="padding: 40px 40px 20px 40px; text-align: center;">
                                <h1 style="margin: 0; color: #1f2937; font-size: 24px; font-weight: 700;">
                                    Verify Your Email
                                </h1>
                            </td>
                        </tr>
                        <tr>
                            <td style="padding: 0 40px 30px 40px; text-align: center;">
                                <p style="margin: 0 0 20px 0; color: #4b5563; font-size: 16px; line-height: 1.6;">
                                    Use the code below to complete your sign-up. This code will expire in 10 minutes.
                                </p>
                                <div style="background-color: #eff6ff; padding: 20px; border-radius: 8px; display: inline-block; margin-bottom: 20px;">
                                    <span style="font-family: monospace; font-size: 32px; font-weight: 700; letter-spacing: 4px; color: #3b82f6;">
                                        {code}
                                    </span>
                                </div>
                                <p style="margin: 0; color: #6b7280; font-size: 14px;">
                                    If you didn't request this code, you can safely ignore this email.
                                </p>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """
    
    # Create email object
    send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
        to=[{"email": to_email}],
        sender={"email": settings.FROM_EMAIL, "name": "Startup Analyst"},
        subject=subject,
        html_content=html_content
    )
    
    try:
        # Send email
        api_instance.send_transac_email(send_smtp_email)
        return True
    except ApiException as e:
        raise Exception(f"Failed to send verification email: {str(e)}")
