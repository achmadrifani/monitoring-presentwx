## Deploy as SystemD Service

`
sudo cp amfoc-streamlit.service /etc/systemd/system
sudo systemctl daemon-reload
sudo systemctl start amfoc-streamlit.service
sudo systemctl status amfoc-streamlit.service
sudo systemctl enable amfoc-streamlit.service
`
