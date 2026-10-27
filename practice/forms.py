from django import forms
from .models import Feedback

class FeedbackForm(forms.ModelForm):
    website = forms.CharField(required=False, widget=forms.HiddenInput)
    class Meta:
        model = Feedback
        fields = ['category','subject','message','name','email','email_updates']
        labels = {'name':'Your name (optional)','email':'Reply email (optional)','message':'Your feedback','email_updates':'Email me a receipt and status updates (optional)'}
        widgets = {'message':forms.Textarea(attrs={'rows':7,'maxlength':4000,'placeholder':'Tell us what happened or what would help. For question corrections, include the component, year and question number.'})}
    def clean_subject(self):
        value = self.cleaned_data['subject'].strip()
        if not value: raise forms.ValidationError('Enter a subject.')
        return value
    def clean_message(self):
        value = self.cleaned_data['message'].strip()
        if not value: raise forms.ValidationError('Enter your feedback.')
        return value

    def clean(self):
        cleaned=super().clean()
        if cleaned.get('email_updates') and not cleaned.get('email'):
            self.add_error('email','Enter your own reply email to receive updates.')
        return cleaned
